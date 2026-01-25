from odoo import models, fields, api
import datetime
from odoo.exceptions import UserError

class account_move_module(models.Model):
    _inherit="account.move"

    id_import = fields.Many2one(
        "x.import",
        string="Importación",
        domain="[('state', '=', 'process')]"
    )

    def action_open_choose_landed_cost_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'choose.landed.cost.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_option': 'create',
                'active_id': self.id,
            },
        }
        
    def button_create_landed_costs(self):
        self.ensure_one()

        skip_check = self.env["ir.config_parameter"].sudo().get_param(
            "penta.skip_import_check_landed_cost", default="True"
        )
        skip_check = skip_check in ("True", "1", True)

        if not skip_check and not self.id_import:
            raise UserError("La factura no tiene un 'Importación' asociado. Asigna uno antes de crear el Costo en Destino.")

        # Llamamos al método original
        result = super().button_create_landed_costs()

        # Obtenemos el costo en destino creado
        landed_cost = self.env['stock.landed.cost'].browse(result['res_id'])

        # Asignamos el campo id_import
        landed_cost.id_import = self.id_import

        # Asignamos esta factura a cada línea de costo
        for line in landed_cost.cost_lines:
            line.account_move_id = self.id

        return result


    has_any_landed_cost = fields.Boolean(compute='_compute_has_any_landed_cost', store=False)

    @api.depends('landed_costs_ids', 'line_ids', 'line_ids.is_landed_costs_line')
    def _compute_landed_costs_visible(self):
        """Mantiene la lógica original + oculta 'Crear costos en destino'
        si la factura YA está en algún LC por líneas (account_move_id)."""
        LcLine = self.env['stock.landed.cost.lines']
        for move in self:
            if move.landed_costs_ids:
                move.landed_costs_visible = False
            else:
                # si existe al menos una línea de LC que apunte a esta factura, también ocultar
                linked_by_lines = bool(LcLine.search_count([('account_move_id', '=', move.id)], limit=1))
                if linked_by_lines:
                    move.landed_costs_visible = False
                else:
                    move.landed_costs_visible = any(line.is_landed_costs_line for line in move.line_ids)

    @api.depends('landed_costs_ids')
    def _compute_has_any_landed_cost(self):
        """True si la factura está vinculada a un LC por vendor_bill_id o por líneas."""
        LcLine = self.env['stock.landed.cost.lines']
        for move in self:
            by_vendor = bool(move.landed_costs_ids)
            by_lines = bool(LcLine.search_count([('account_move_id', '=', move.id)], limit=1))
            move.has_any_landed_cost = by_vendor or by_lines

    def action_view_landed_costs(self):
        """Abrir TODOS los LCs ligados a la factura:
           - Por vendor_bill_id
           - Por líneas con account_move_id = factura
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        domain = ['|',
                  ('vendor_bill_id', '=', self.id),
                  ('cost_lines.account_move_id', '=', self.id)]
        context = dict(self.env.context, default_vendor_bill_id=self.id)
        views = [
            (self.env.ref('stock_landed_costs.view_stock_landed_cost_tree2').id, 'list'),
            (False, 'form'),
            (False, 'kanban'),
        ]
        return dict(action, domain=domain, context=context, views=views)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Trae la guía de importación desde la factura/asiento
    id_import = fields.Many2one(
        'x.import',
        string='Guía de importación',
        related='move_id.id_import',
        store=True,       # <— guarda en DB para poder filtrar/ordenar/agrup.
        index=True,
        readonly=True,
    )