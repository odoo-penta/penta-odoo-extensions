# models/res_country_state_city.py
from odoo import models, fields, api, _
import re

class ResCountryStateCity(models.Model):
    _name = 'res.country.state.city'
    _description = 'Ciudades (Cantones)'

    name = fields.Char(required=True, index=True)
    code = fields.Char(string="Código (2 dígitos)", required=True, index=True)  # <- 2 dígitos finales del cantón
    state_id = fields.Many2one('res.country.state', string="Provincia", required=True, index=True)
    country_id = fields.Many2one('res.country', string="País", required=True, index=True)

    _sql_constraints = [
        ('uniq_city_code_per_state',
         'unique(code, state_id)',
         'El código de ciudad debe ser único dentro de la provincia.'),
    ]

    @api.constrains('code')
    def _check_code_len(self):
        for rec in self:
            if not rec.code or not re.fullmatch(r'\d{2}', rec.code):
                raise ValueError("El código de ciudad debe tener exactamente 2 dígitos.")
