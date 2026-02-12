from odoo import models, fields

class WithholdingConfirmWizard(models.TransientModel):
    _name = 'withholding.confirm.wizard'
    _description = 'Confirmar creación de retención'

    archivo_id = fields.Many2one(
        'archivo.model',
        required=True
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura encontrada',
        readonly=True
    )

    def action_continue(self):
        self.archivo_id.create_retention()
        return {'type': 'ir.actions.act_window_close'}
