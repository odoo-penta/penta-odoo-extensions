# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProcessLineWizard(models.TransientModel):
    _name = "process.line.wizard"
    _description = "Process Line Wizard"

    production_id = fields.Many2one(
        'mrp.production',
        string="Manufacturing Order",
        required=True,
        readonly=True
    )

    qty_to_produce = fields.Integer(
        string="Quantity to Produce",
        required=True,
        default=1
    )

    @api.constrains('qty_to_produce')
    def _check_qty(self):
        for wiz in self:
            if wiz.qty_to_produce <= 0:
                raise UserError(_("Quantity must be greater than zero."))

    def action_confirm(self):
        self.ensure_one()
        production = self.production_id

        # -----------------------------
        # VALIDACIONES BASE
        # -----------------------------
        if production.state not in ('confirmed', 'progress'):
            raise UserError(_("Production must be confirmed or in progress."))

        if production.product_id.tracking != 'serial':
            raise UserError(_("This wizard is only for serial-tracked products."))

        remaining = production.product_qty - production.qty_produced
        if remaining <= 0:
            raise UserError(_("Nothing left to produce."))

        qty = min(self.qty_to_produce, remaining)

        # -----------------------------
        # CKD DEFINIDOS EN LA MO (UNA SOLA VEZ)
        # -----------------------------
        ckd_move = production.move_raw_ids.filtered(
            lambda m: m.product_id.tracking == 'serial'
        )[:1]

        if not ckd_move:
            raise UserError(_("No serial-tracked CKD found in components."))

        # SOLO DATOS INMUTABLES (NOMBRES DE LOTES)
        ckd_lot_names = ckd_move.move_line_ids.filtered(
            lambda ml: ml.lot_id
        ).mapped('lot_id.name')

        if len(ckd_lot_names) < qty:
            raise UserError(_("Not enough CKD serials assigned to this MO."))

        # -----------------------------
        # PRODUCCIÓN SERIAL CONTROLADA
        # -----------------------------
        for i in range(qty):
            # 🔑 qty_producing SIEMPRE acumulativo
            production.qty_producing = production.qty_produced + 1

            ckd_lot_name = ckd_lot_names[i]

            # Crear / reutilizar lote del producto terminado
            finished_lot = self.env['stock.lot'].search([
                ('product_id', '=', production.product_id.id),
                ('company_id', '=', production.company_id.id),
                ('name', '=', ckd_lot_name),
            ], limit=1)

            if not finished_lot:
                finished_lot = self.env['stock.lot'].create({
                    'product_id': production.product_id.id,
                    'company_id': production.company_id.id,
                    'name': ckd_lot_name,
                })

            # Asignar serial al producto terminado
            production.lot_producing_id = finished_lot.id

            production._post_inventory(cancel_backorder=False)

        # -----------------------------
        # CERRAR SOLO SI YA SE PRODUJO EN SU TOTALIDAD
        # -----------------------------
        if production.qty_produced >= production.product_qty:
            production.button_mark_done()

        return {'type': 'ir.actions.act_window_close'}
