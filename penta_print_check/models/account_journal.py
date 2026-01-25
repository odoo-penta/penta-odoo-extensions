# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = "account.journal"

    ec_check_print_format_id = fields.Many2one(
        "ec.check.print.format",
        string="Check format",
        domain="[('active','=',True)]",
        help="Editable format for printing checks",
    )
