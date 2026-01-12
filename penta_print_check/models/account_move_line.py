# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    check_debit = fields.Char(compute="_compute_check_debit", string="Check debit", help="Debit with decimals to print on the check")
    check_credit = fields.Char(compute="_compute_check_credit", string="Check credit", help="Credit with decimals to print on the check")
    
    @api.depends('debit')
    def _compute_check_debit(self):
        for line in self:
            if line.currency_id:
                line.check_debit = line.currency_id.format(line.debit).replace('$', '').replace('\u00A0', '').strip()
            else:
                line.check_debit = str(line.debit or 0.0)
                
    @api.depends('credit')
    def _compute_check_credit(self):
        for line in self:
            if line.currency_id:
                line.check_credit = line.currency_id.format(line.credit).replace('$', '').replace('\u00A0', '').strip()
            else:
                line.check_credit = str(line.credit or 0.0)