# -*- coding: utf-8 -*-
from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    account_withhold = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta retencion'
    )
