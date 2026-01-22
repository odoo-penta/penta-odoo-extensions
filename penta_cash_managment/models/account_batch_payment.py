from odoo import models, api

class AccountBatchPaymentModel(models.Model):
    _inherit = 'account.batch.payment'

    def action_print_batch_payment(self, **kwargs):
        journal = self.journal_id

        wizard = self.env['batch.payment.popup.wizard'].create({
            'batch_payment_id': self.id,  # Pasar el ID del registro actual
            'journal_id': journal.id, 
            'bank_format_ids': [(6, 0, journal.penta_cash_bank_format_ids.ids)]
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asistente de reportes',
            'res_model': 'batch.payment.popup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': self.env.ref('penta_cash_managment.view_batch_payment_popup_wizard_form').id,
            'res_id': wizard.id,  # Aquí pasamos el ID del wizard recién creado
        }
    