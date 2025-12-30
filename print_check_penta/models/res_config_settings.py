# -*- coding: utf-8 -*-

from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ec_check_print_format_id = fields.Many2one(
        related="company_id.ec_check_print_format_id",
        config_parameter='print_check_penta.ec_check_print_format_id',
        company_dependent=True,
        string="Default check print format", readonly=False,
        help="This check format will be used by default when printing checks."
    )
