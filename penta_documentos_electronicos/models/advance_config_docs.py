from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AdvanceConfigDocs(models.Model):
    _name = 'advance.config.docs'
    _description = 'Configuración de Diario de Retenciones'

    advance_docs_journal_id = fields.Many2one(
        'account.journal',
        string='Diario de Retenciones',
        help='Diario utilizado para registrar las retenciones.'
    )

    def unlink(self):
        raise UserError(_('No se puede eliminar la configuración de anticipos. Solo puede ser editada.'))