from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_ensabled = fields.Boolean(
        string="Producto ensamblado?",
        help="Indica si el producto es ensamblado para aplicar ICE."
    )