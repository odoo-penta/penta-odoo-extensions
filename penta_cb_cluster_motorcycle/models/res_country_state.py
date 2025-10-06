from odoo import api, fields, models, _
from odoo.exceptions import UserError



class ResCountryState(models.Model):
    _inherit = 'res.country.state'
    
    l10n_ec_penta_code_state = fields.Char(string='EC Penta Code',
                                 help='Código de la provincia según el SRI (Ecuador).')
