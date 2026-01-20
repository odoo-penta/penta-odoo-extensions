from odoo import models, fields

class AccountPayment(models.Model):
    _inherit = "account.payment"

    id_import = fields.Many2one(
        "x.import",
        string="Importación",
        domain="[('state', '=', 'process')]"
    )