from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResCity(models.Model):
    _inherit = 'res.city'
    
    l10n_ec_penta_code_city = fields.Char(
                                compute='_compute_l10n_ec_penta_code_city',
                                string='EC City Code',
                                help='Código de la ciudad según el SRI (Ecuador).',
                                store=True)
    
    
    
    
    @api.depends('l10n_ec_code', 'state_id.l10n_ec_penta_code_state')
    def _compute_l10n_ec_penta_code_city(self):
        for record in self:
            if record.state_id.l10n_ec_penta_code_state:
                record.l10n_ec_penta_code_city = f"{record.state_id.l10n_ec_penta_code_state}{record.l10n_ec_code if len(record.l10n_ec_code) == 2 else '0'+record.l10n_ec_code}"
            else:
                record.l10n_ec_penta_code_city = False