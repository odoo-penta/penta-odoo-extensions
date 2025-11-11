# models/account_move.py
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from math import prod

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"


    @api.depends('price_unit', 'discount', 'quantity', 'tax_ids')
    def _compute_price(self):
        # Reutilizamos la lógica de Odoo y la ajustamos
        for line in self:
            # Base imponible después del descuento
            base = line.price_unit * line.quantity * (1 - (line.discount or 0.0) / 100)

            # Calculamos los impuestos (incluye ICE)
            taxes = line.tax_ids.compute_all(
                line.price_unit,
                quantity=line.quantity,
                currency=line.move_id.currency_id,
                product=line.product_id,
                partner=line.move_id.partner_id
            )

            # Reemplazamos la base para que los impuestos se apliquen sobre base ya ajustada
            # Esto fuerza el cálculo correcto con descuento aplicado
            price_subtotal = base
            price_total = price_subtotal + sum(t['amount'] for t in taxes['taxes'])

            line.price_subtotal = price_subtotal
            line.price_total = price_total