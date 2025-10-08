from odoo import models, fields, _


class AccountTax(models.Model):
    _inherit='account.tax'
    
    
    apply_to_unit_price = fields.Boolean(string = _("Applied under unit price"),
                                       help= _("This field is for knowing if the tax applied to unit price"))