# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    def _get_check_print_format(self):
        self.ensure_one()

        if self.journal_id.ec_check_print_format_id:
            return self.journal_id.ec_check_print_format_id

        param = self.env['ir.config_parameter'].sudo().get_param(
            'print_check_penta.default_format_id'
        )
        if param:
            fmt = self.env['ec.check.print.format'].browse(int(param))
            if fmt.exists():
                return fmt

        raise UserError(_("There is no check format configured. Configure one in the journal or in the general settings."))
    
    def do_print_checks(self):
        self.ensure_one()
        if self.payment_method_line_id.code != 'check_printing':
            raise UserError(_("This payment is not set up to print checks."))
        return {
            'name': _('Print check'),
            'type': 'ir.actions.act_window',
            'res_model': 'print.check.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_id': self.id,
            }
        }
    """
    def do_print_checks(self):
        self.ensure_one()
        
        fmt = self._get_check_print_format()
        
        if fmt.orientation == 'landscape':
            check_layout = 'print_check_penta.action_report_check_landscape_penta'
        else:
            check_layout = 'print_check_penta.action_report_check_portrait_penta'
        
        report_action = self.env.ref(check_layout, False)
        
        if not report_action:
            raise UserError(_("The configured check layout was not found."))
        #self.write({'is_sent': True})
        import pdb;pdb.set_trace()
        return report_action.report_action(self)
    """
