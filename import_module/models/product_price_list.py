# models/product_pricelist.py (crear si no existe ya un archivo que herede)
from odoo import models, fields

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    sri_list_price = fields.Boolean(string="Lista SRI", help="Marcar esta lista si se usa para el cálculo del valor original en importaciones.")
