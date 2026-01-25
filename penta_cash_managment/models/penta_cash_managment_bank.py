
from odoo import api, fields, models

class PentaCashManagmentBank(models.Model):
    _name = "penta.cash.managment.bank"
    _description = "Penta - Cash Management Bank Formats"

    name = fields.Char("Banco", required=True)
    code = fields.Char("Código de formato", required=True)

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'El código del formato debe ser único.')
    ]
