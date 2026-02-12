from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    bank_withholding_agent = fields.Boolean(string='Emisor de Retención Bancaria', help='Indica si el partner es emisor de retención bancaria')