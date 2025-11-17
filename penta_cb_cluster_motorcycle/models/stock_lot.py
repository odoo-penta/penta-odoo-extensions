# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockLot(models.Model):
    _inherit = 'stock.lot'

    motor_number = fields.Char()
    ramv = fields.Char()
    plate = fields.Char(string="Plate",help="Enter the license plate number.")

class ProjectTaskInherit(models.Model):
    _inherit = 'project.task'

    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string="Chassis",
        help="Select the chassis related to this task."
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        related='lot_id.product_id',
        store=True,
        readonly=True
    )