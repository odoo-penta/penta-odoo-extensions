from odoo import models, fields, api
import datetime
from odoo.exceptions import UserError

class purchase_module(models.Model):
    _inherit="purchase.order"

    id_import = fields.Many2one(
        "x.import",
        string="Importación",
        domain="[('state', '=', 'process')]"
    )

    def _get_related_receipts(self):
        """Pickings de recepción vinculados a la PO por origin o por sus movimientos."""
        self.ensure_one()
        Picking = self.env['stock.picking']
        domain = [
            ('picking_type_code', '=', 'incoming'),
            ('company_id', '=', self.company_id.id),
            ('state', '!=', 'cancel'),
            '|',
            ('origin', '=', self.name),
            ('move_ids.purchase_line_id.order_id', '=', self.id),  # relación por movimientos
        ]
        return Picking.search(domain)

    def write(self, vals):
        import_changed = 'id_import' in vals
        res = super().write(vals)

        if import_changed:
            for po in self:
                pickings = po._get_related_receipts()
                if not pickings:
                    continue
                new_import_id = po.id_import.id  # valor final post-write (puede ser False)
                # Evita writes innecesarios
                to_update = pickings.filtered(lambda p: (p.id_import.id or False) != (new_import_id or False))
                if to_update:
                    to_update.sudo().write({'id_import': new_import_id})
        return res