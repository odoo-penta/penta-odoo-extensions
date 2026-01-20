from odoo import models, fields

class CustomsRegime(models.Model):
    _name = 'x.customs.regime'
    _description = 'Régimen Aduanero'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)
    description = fields.Text(string='Descripción')
                                                            