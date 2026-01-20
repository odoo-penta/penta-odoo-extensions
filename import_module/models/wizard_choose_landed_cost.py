# models/wizard_choose_landed_cost.py
from odoo import models, fields, api
from odoo.exceptions import UserError
class ChooseLandedCostWizard(models.TransientModel):
    _name = 'choose.landed.cost.wizard'
    _description = 'Seleccionar o crear costo en destino'

    option = fields.Selection([
        ('associate', 'Asociar la factura con un costo en destino'),
        ('create', 'Crear nuevo costo en destino'),
    ], string="Opción", required=True)

    landed_cost_id = fields.Many2one(
        'stock.landed.cost', 
        string='Costo en destino',
        domain=[('state', '=', 'draft')]
    )

    def action_confirm(self):
        self.ensure_one()
        move = self.env['account.move'].browse(self.env.context.get('active_id'))

        # 1. La factura debe tener guía de importación
        if not move.id_import:
            raise UserError("La factura debe tener asignada una Guía de Importación antes de continuar.")

        # -------------------------------------------------------------------
        # CASO 1: ASOCIAR A UN LANDED COST EXISTENTE
        # -------------------------------------------------------------------
        if self.option == 'associate':

            # --- 1.1 Valida / asigna id_import al landed cost ---
            if self.landed_cost_id.id_import:
                if self.landed_cost_id.id_import != move.id_import:
                    raise UserError("No se puede asociar: la 'Guía de Importación' de la factura "
                                    "no coincide con la del costo en destino seleccionado.")
            else:
                self.landed_cost_id.id_import = move.id_import

            # --- 1.2 Calcular FOB total ordenado ---
            origin_names = self.landed_cost_id.picking_ids.mapped('origin')
            purchases = self.env['purchase.order'].search([('name', 'in', origin_names)])

            total_fob_ordered = sum(
                pol.product_qty * pol.price_unit
                for pol in purchases.mapped('order_line')
            )
            if not total_fob_ordered:
                raise UserError("No se encontraron valores FOB en las órdenes de compra vinculadas.")

            # ---------------------------------------------
            # 1.3 Calcular FOB recibido con move_ids_without_package
            # ---------------------------------------------
            moves = self.landed_cost_id.picking_ids.mapped('move_ids_without_package')
            fob_recibido = sum(
                mv.quantity * mv.purchase_line_id.price_unit
                for mv in moves
                if mv.purchase_line_id
            )
            if not fob_recibido:
                raise UserError(
                    "No hay valor FOB recibido aún en los pickings asociados."
                )

            factor = fob_recibido / total_fob_ordered

            # --- 1.4 Crear líneas del landed cost proporcionalmente ---
            landed_cost_lines = []
            for line in move.line_ids.filtered(lambda l: l.is_landed_costs_line):
                original_price = line.currency_id._convert(
                    line.price_subtotal,
                    line.company_currency_id,
                    line.company_id,
                    move.invoice_date or fields.Date.context_today(line),
                )
                proportional_price = original_price * factor

                landed_cost_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'account_id': line.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id,
                    'price_unit': proportional_price,
                    'split_method': line.product_id.split_method_landed_cost or 'equal',
                    'account_move_id': move.id,
                }))

            self.landed_cost_id.write({
                'vendor_bill_id': move.id,
                'cost_lines': landed_cost_lines,
            })
            move.landed_costs_ids = [(4, self.landed_cost_id.id)]

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.landed.cost',
                'res_id': self.landed_cost_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # -------------------------------------------------------------------
        # CASO 2: CREAR UN NUEVO LANDED COST DESDE LA FACTURA
        # -------------------------------------------------------------------
        else:
            action = move.with_context(from_wizard=True).button_create_landed_costs()
            return action