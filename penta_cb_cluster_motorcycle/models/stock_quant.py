# -*- coding: utf-8 -*-
from odoo import fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    product_default_code = fields.Char(
        string="Referencia interna",
        related="product_id.default_code",
        store=True,
        readonly=True,
    )
    product_name = fields.Char(
        string="Nombre",
        related="product_id.name",
        store=True,
        readonly=True,
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Almacen",
        related="location_id.warehouse_id",
        store=True,
        readonly=True,
    )
