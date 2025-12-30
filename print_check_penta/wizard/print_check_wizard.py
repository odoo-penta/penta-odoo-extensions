# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError

class PrintCheckWizard(models.TransientModel):
    _name = 'print.check.wizard'
    _description = 'Print check wizard'

    payment_id = fields.Many2one(
        'account.payment',
        string="Payment",
        required=True,
        readonly=True,
    )

    def action_print(self):
        self.ensure_one()
        import pdb;pdb.set_trace()
        payment = self.payment_id
        
        fmt = payment._get_check_print_format()
        
        if fmt.orientation == 'landscape':
            check_layout = 'print_check_penta.action_report_check_landscape_penta'
        else:
            check_layout = 'print_check_penta.action_report_check_portrait_penta'
            
        report_action = self.env.ref(check_layout, False)
        
        #return report_action.report_action(payment)
        return report_action.with_context(
            active_ids=[payment.id],
            active_model='account.payment',
            report_pdf_no_attachment=True,
        ).report_action(payment)
