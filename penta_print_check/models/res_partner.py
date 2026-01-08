# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    name_print_check = fields.Char()
