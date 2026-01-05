# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.tools import split_amount

class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    def _get_check_print_format(self):
        self.ensure_one()

        if self.journal_id.ec_check_print_format_id:
            return self.journal_id.ec_check_print_format_id

        param = self.env['ir.config_parameter'].sudo().get_param(
            'penta_print_check.default_format_id'
        )
        if param:
            fmt = self.env['ec.check.print.format'].browse(int(param))
            if fmt.exists():
                return fmt

        raise UserError(_("There is no check format configured. Configure one in the journal or in the general settings."))

    def do_print_checks(self):
        self.ensure_one()
        
        fmt = self._get_check_print_format()
        
        if fmt.orientation == 'landscape':
            check_layout = 'penta_print_check.action_report_check_landscape_penta'
        else:
            check_layout = 'penta_print_check.action_report_check_portrait_penta'
        
        report_action = self.env.ref(check_layout, False)
        
        if not report_action:
            raise UserError(_("The configured check layout was not found."))
        #self.write({'is_sent': True})
        #import pdb;pdb.set_trace()
        return report_action.report_action(self)
    
    @api.depends('payment_method_line_id', 'currency_id', 'amount')
    def _compute_check_amount_in_words(self):
        """ Override to support the specific format for the cheques."""
        super(AccountPayment, self)._compute_check_amount_in_words()
        for pay in self:
            integer_part, decimal_part = split_amount(pay.amount)
            if pay.currency_id:
                amount_text = pay.currency_id.amount_to_text(integer_part).strip()
                amount_text = amount_text.replace('Dollars', '').replace('Dollar', '').replace('Dólares', '').replace('Dólar', '').strip()
                amount_text += f' {str(decimal_part).ljust(2, "0")}/100 Dólares'
                pay.check_amount_in_words = amount_text
            else:
                pay.check_amount_in_words = False
        

