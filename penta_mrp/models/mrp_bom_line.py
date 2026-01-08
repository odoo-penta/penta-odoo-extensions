# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    total_mp_cost = fields.Float(
        string='Total Material Cost',
        compute='_compute_total_mp_cost',
        store=True,
        help='Total material cost based on standard price and quantity.'
    )

    @api.depends('standard_price', 'product_qty')
    def _compute_total_mp_cost(self):
        for record in self:
            record.total_mp_cost = record.standard_price * record.product_qty
