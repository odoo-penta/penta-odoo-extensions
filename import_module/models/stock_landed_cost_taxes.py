# models/stock_landed_cost_taxes.py
from odoo import models, fields, api

class StockLandedCostTaxes(models.Model):
    _name = 'stock.landed.cost.taxes'
    _description = 'Impuestos sobre Costo en Destino'

    product_id = fields.Many2one('product.product', string='Producto')
    tariff_item_id = fields.Many2one('tariff.item', string='Partida Arancelaria', store=True)
    quantity = fields.Float(string='Cantidad')
    value_original_unit = fields.Float(string='Valor Original (Unitario)', store=True)
    cif = fields.Float(string='CIF', store=True)
    percentage = fields.Float(string="Porcentaje")
    tax_value = fields.Float(string='Valor de Impuesto', store=True)
    cost_line = fields.Char(string='Línea de Costo')

    landed_cost_id = fields.Many2one(
        'stock.landed.cost',
        string='Costo en destino',
        ondelete='cascade'
    )
    
    val_line_id = fields.Many2one(
        'stock.valuation.adjustment.lines',
        string='VAL origen',
        index=True
    )
    
    cost_product_id = fields.Many2one('product.product', string='Producto de costo', index=True)