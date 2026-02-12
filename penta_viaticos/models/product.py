from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    importe_permitido = fields.Monetary(
        string = "Valor permitido",
        help = "Valor maximo permitido para este rubro de viáticos",
        currency_field="currency_id"
    )

class ProductProduct(models.Model):
    _inherit = "product.product"
    importe_permitido = fields.Monetary(
        related = "product_tmpl_id.importe_permitido",
        readonly=False,
        store=True,
        currency_field="currency_id"
    )
