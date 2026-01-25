# -*- coding: utf-8 -*-
from odoo import models, fields

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # Toma el id_import directamente del picking
    id_import = fields.Many2one(
        'x.import',
        string='Guía de importación',
        related='picking_id.id_import',
        store=True,
        index=True,
        readonly=True,
        copy=False,
    )
