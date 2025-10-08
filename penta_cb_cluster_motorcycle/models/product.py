# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'
    
    hide_pdf = fields.Boolean()
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    is_ensabled = fields.Boolean(string=_("Ensabled product ?"),
                                 help=_("Field that indicate if the product is ensabled"))