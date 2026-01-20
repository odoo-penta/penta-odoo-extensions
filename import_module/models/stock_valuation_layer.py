# models/stock_valuation_layer.py
from odoo import models, fields

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    # Related al id_import del asiento contable
    id_import = fields.Many2one(
        'x.import',
        string='Guía de importación',
        related='stock_move_id.picking_id.id_import',
        store=True,
        index=True,
        readonly=True,
        copy=False,
    )
