from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_ensabled = fields.Boolean(string=_("Ensabled product ?"),
                                 help=_("Field that indicate if the product is ensabled"))