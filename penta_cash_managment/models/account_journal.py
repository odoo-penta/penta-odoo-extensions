from odoo import models, fields, api
import datetime
from odoo.exceptions import UserError

class account_journal_model(models.Model):
    _inherit="account.journal"

    penta_cash_bank_format_ids = fields.Many2many(
        "penta.cash.managment.bank",
        string="Bancos / formatos de pago"
    )

    penta_cash_management_code = fields.Char(
        string="Código de Cash Management"
    )

    penta_company_code = fields.Char(
        string="Código de empresa (banco)"
    )

    penta_company_mnemonic = fields.Char(
        string="Nemónico de empresa"
    )