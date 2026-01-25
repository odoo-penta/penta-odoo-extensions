# -*- coding: utf-8 -*-

from odoo import models, fields

class EcCheckPrintFormat(models.Model):
    _name = "ec.check.print.format"
    _description = "Check printing format"
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
    _order = "pos_y asc, pos_x asc"

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
        ('city', 'City'),
        ('account_name', 'Account Name'),
        ('account_code', 'Account Code'),
        ('payment_name', 'Payment Name'),
        ('payment_number', 'Payment Number'),
        ('payment_concept', 'Payment Concept'),
        ('move_account_code', 'Move Account Code'),
        ('move_account_name', 'Move Account Name'),
        ('move_account_debit', 'Move Account Debit'),
        ('move_account_credit', 'Move Account Credit'),
        ('move_account_total_debit', 'Move Account Total Debit'),
        ('move_account_total_credit', 'Move Account Total Credit'),
    ], required=True)
    pos_x = fields.Float(string="X (mm)", required=True)
    pos_y = fields.Float(string="Y (mm)", required=True)
    font_size = fields.Float(string="Font size (pt)", default=12.0, help="Font size in points (pt)")
    text_align = fields.Selection([
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right'),
    ], string="Text alignment", default='left')
    width = fields.Float(string="Width (mm)", help="Width of the field in millimeters")
    height = fields.Float(
        string="Height (pt)",
        help="Height in points (pt). If not defined, 1.2 * font_size will be used."
    )

    
