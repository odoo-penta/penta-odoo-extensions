# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import split_amount

class AccountPayment(models.Model):
    _inherit = "account.payment"

    check_beneficiary = fields.Many2one('res.partner', string='Check Beneficiary', help='The beneficiary of the check.')
    check_amount = fields.Char(compute="_compute_check_amount", string="Check amount", help="Amount with decimals to print on the check")
    
    @api.depends('amount')
    def _compute_check_amount(self):
        for payment in self:
            if payment.currency_id:
                payment.check_amount = payment.currency_id.format(
                    payment.amount,
                    currency=payment.currency_id,
                    grouping=True
                )
            else:
                payment.check_amount = str(payment.amount or 0.0)

    def _get_check_print_format(self):
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
        fmt = self._get_check_print_format()
        
        if fmt.orientation == 'landscape':
            check_layout = 'penta_print_check.action_report_check_landscape_penta'
        else:
            check_layout = 'penta_print_check.action_report_check_portrait_penta'
        
        report_action = self.env.ref(check_layout, False)
        
        if not report_action:
            raise UserError(_("The configured check layout was not found."))
        self.write({'is_sent': True})
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
                
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for record in self:
            if record.partner_id and not record.check_beneficiary:
                record.check_beneficiary = record.partner_id
        

