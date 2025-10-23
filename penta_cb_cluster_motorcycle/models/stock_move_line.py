# -*- coding: utf-8 -*-
from odoo import models, fields


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    motor_number =fields.Char()
    ramv =fields.Char()