# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'
    
    hide_pdf = fields.Boolean()