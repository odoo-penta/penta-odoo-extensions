# -*- coding: utf-8 -*-

from odoo import fields, models, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    standard_price_customer = fields.Float(
        string='Standard Price Customer',
        help='Precio estándar para el cliente',
        digits='Product Price'
    )