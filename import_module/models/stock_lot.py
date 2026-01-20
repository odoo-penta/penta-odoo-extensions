from odoo import models, fields, api

class StockLot(models.Model):
    _inherit = 'stock.lot'

    import_id = fields.Many2one('x.import', string='Importación', compute='_compute_import_id', store=False)

    def _compute_import_id(self):
        for lot in self:
            import_id = False
            purchase_orders = lot.purchase_order_ids

            import_ids = purchase_orders.mapped('id_import')
            if import_ids:
                import_id = import_ids[0]

            lot.import_id = import_id
