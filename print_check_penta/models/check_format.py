# -*- coding: utf-8 -*-

from odoo import models, fields

class EcCheckPrintFormat(models.Model):
    _name = "ec.check.print.format"
    _description = "Formato de Impresión de Cheques"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    orientation = fields.Selection(
        [('portrait', 'Portrait'), ('landscape', 'Landscape')],
        string='Orientation',
        required=True,
        help='Orientation used for this check layout',
    )
    line_ids = fields.One2many(
        "ec.check.print.format.line",
        "format_id",
        string="Print lines",
    )
    
class EcCheckPrintFormatLine(models.Model):
    _name = "ec.check.print.format.line"
    _description = "Cheque Print Line"

    format_id = fields.Many2one(
        "ec.check.print.format",
        required=True,
        ondelete="cascade",
    )
    field_key = fields.Selection([
        ('date', 'Date'),
        ('partner', 'Beneficiary'),
        ('amount', 'Amount'),
        ('amount_text', 'Amount in words'),
        ('reference', 'Reference'),
        ('check_number', 'Check number'),
    ], required=True)
    pos_x = fields.Float(string="X (mm)", required=True)
    pos_y = fields.Float(string="Y (mm)", required=True)
    font_size = fields.Float(string="Font size (pt)", default=10.0, help="Font size in points (pt)")
    
