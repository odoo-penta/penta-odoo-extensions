from odoo import models, fields, api

class AccountMoveStock(models.Model):
    _inherit = 'account.move'

    stock_lot_ids = fields.One2many(
        'stock.lot',
        compute='_compute_stock_lot_ids',
        string="Lotes Relacionados",
        store=False
    )

    @api.depends('invoice_line_ids')
    def _compute_stock_lot_ids(self):
        """Obtiene los lotes realmente facturados desde move._get_invoiced_lot_values()."""
        for move in self:

            lots = self.env['stock.lot']

            # Obtener todos los lotes facturados de la factura completa
            invoiced_lots_data = move._get_invoiced_lot_values()

            if invoiced_lots_data:
                invoiced_lot_ids = [d['lot_id'] for d in invoiced_lots_data if d.get('lot_id')]
                lots = self.env['stock.lot'].browse(invoiced_lot_ids)

            move.stock_lot_ids = lots
