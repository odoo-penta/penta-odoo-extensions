from odoo import models, fields, _


class AccountTax(models.Model):
    _inherit='account.tax'
    
    
    apply_on_unit_price = fields.Boolean(
        string="Aplica sobre Precio Unitario?",
        help="Si está activo, el impuesto se calcula sobre price_unit."
    )