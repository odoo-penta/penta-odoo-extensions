# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'
    
    hide_pdf = fields.Boolean()