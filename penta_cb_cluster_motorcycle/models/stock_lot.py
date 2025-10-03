# -*- coding: utf-8 -*-
from odoo import models, fields


class StockLot(models.Model):
    _inherit = 'stock.lot'

    motor_number = fields.Char()
    ramv = fields.Char()
    national_production_code = fields.Char()
