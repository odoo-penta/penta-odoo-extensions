from odoo.exceptions import UserError
from odoo import models, fields

class TariffItemLine(models.Model):
    _name = 'tariff.item.line'
    _description = 'Línea de Partida Arancelaria'

    tariff_item_id = fields.Many2one(
        'tariff.item',
        string='Partida Arancelaria',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        domain="[('product_tmpl_id.landed_cost_type', '=', 'customs')]"
    )
    date_from = fields.Date(string='Fecha Desde')
    percentage = fields.Float(string='Porcentaje %')

