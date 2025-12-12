# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # CPN/PDI en Process Lines (relacionados al lote)
    cpn_display = fields.Char(string="CPN", related="lot_id.cpn", store=False, readonly=True)
    pdi_display = fields.Char(string="PDI", related="lot_id.pdi", store=False, readonly=True)

    def action_generate_cpn_pdi_line(self):
        """Abrir wizard para GENERAR SOLO ESTA LÍNEA de producto terminado."""
        self.ensure_one()
        prod = self.move_id.production_id
        if not prod or prod.state not in ("confirmed", "progress"):
            raise UserError(_("La orden debe estar en estado 'Listo' o 'En Progreso'."))
        if self.product_id.tracking == "none":
            raise UserError(_("La línea seleccionada no requiere lote/serie."))

        return {
            "type": "ir.actions.act_window",
            "res_model": "generate.cpn.pdi.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_production_id": prod.id,
                "default_move_line_id": self.id,
            },
        }