from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_raw_material = fields.Boolean(
        string="Is it raw material??",
        help="Indicate whether the product is a raw material in production"
    )