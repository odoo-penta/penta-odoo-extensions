# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    program_type = fields.Selection(
        selection_add=[
            ('financing_promotion', 'Financing promotion')
        ], ondelete={'financing_promotion': 'cascade'}
    )
    @api.model
    def _program_items_name(self):
        res = super()._program_items_name()
        res.update({
            'financing_promotion': _('Financing promotion'),
        })
        return res
