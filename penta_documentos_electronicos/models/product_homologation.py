from odoo import models, fields, api


class ProductHomologation(models.Model):
    _name = 'product.homologation'
    _description = 'Modelo para homologar productos'

    etiqueta = fields.Char(string='Etiqueta')
    product_variant_id = fields.Many2one(
        'product.product', 
        string='Producto', 
        required=True
    )