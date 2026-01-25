# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    ec_check_print_format_id = fields.Many2one(
        "ec.check.print.format",
        string="Default check format",
        help="Format used when printing checks",
    )
