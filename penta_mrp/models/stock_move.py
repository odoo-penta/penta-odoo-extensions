# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    price_total = fields.Float(
        string="Total",
        compute="_compute_price_total",
        store=True
    )

    @api.depends('standard_price_invisible', 'quantity')
    def _compute_price_total(self):
        for move in self:
            move.price_total = move.standard_price_invisible * move.quantity    
