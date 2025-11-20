# models/account_move.py
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from math import prod

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"


    def _compute_totals(self):
        super()._compute_totals()
        for line in self:
            if line.display_type:
                continue
            if not line.product_id or not line.product_id.is_ensabled:
                continue
            ice_taxes = line.tax_ids.filtered(lambda t: t.apply_on_unit_price)
            if not ice_taxes:
                continue
            ice_total = 0
            for tax in ice_taxes:
                if tax.amount_type == "percent":
                    ice_total += (tax.amount / 100.0) * line.price_unit
                else:
                    ice_total += tax.amount
            line.price_tax = ice_total
            line.price_total = line.price_subtotal + ice_total