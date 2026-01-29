from odoo import models, fields, api, _

class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    region_id = fields.Many2one('res.country.state.region', string='Region', index=True)
