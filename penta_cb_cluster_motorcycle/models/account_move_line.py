# models/account_move.py
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from math import prod

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # Guarda los impuestos que deben aplicarse sobre el precio unitario
    unit_price_tax_ids = fields.Many2many(
        "account.tax",
        string="Impuestos al precio unitario",
        help="Impuestos con apply_to_unit_price=True detectados en la línea.",
    )

    # Precio base sin los impuestos 'unitarios' (para no acumular multiplicaciones)
    price_unit_base = fields.Float(
        string="Precio base (técnico)",
        digits="Product Price",
        help="Precio unitario antes de sumar impuestos con apply_to_unit_price.",
    )

    @api.onchange("product_id")
    def _onchange_set_base_from_product(self):
        """Cada vez que el usuario elige producto, captura el price_unit actual como base."""
        for line in self:
            if line.display_type:
                continue
            # Cuando se elige producto, Odoo ya calculó price_unit (list_price/descuentos/pricelist)
            line.price_unit_base = line.price_unit or 0.0

    @api.onchange("product_id", "tax_ids")
    def _onchange_apply_unit_price_taxes(self):
        """
        Captura el momento de agregar la línea / cambiar impuestos:
        - Separa los impuestos 'unitarios' (apply_to_unit_price=True).
        - Los quita de tax_ids para que no apliquen sobre subtotal.
        - Ajusta price_unit = base + (porcentaje sobre base) + (fijos por unidad).
        - Guarda los unitarios en unit_price_tax_ids.
        """
        for line in self:
            if line.display_type:
                continue
            if not line.product_id:
                # sin producto no hay nada que hacer
                line.unit_price_tax_ids = [(6, 0, [])]
                continue

            # 1) separar impuestos
            taxes_unit = line.tax_ids.filtered(lambda t: getattr(t, "apply_to_unit_price", False))
            taxes_normal = line.tax_ids - taxes_unit

            # 2) persistir los "unitarios" y dejar sólo normales en tax_ids
            line.unit_price_tax_ids = [(6, 0, taxes_unit.ids)]
            line.tax_ids = [(6, 0, taxes_normal.ids)]

            # 3) precio base: si no está seteado (p.ej. primera vez), tómalo del price_unit actual
            base = line.price_unit_base if line.price_unit_base else (line.price_unit or 0.0)
            line.price_unit_base = base  # asegúrate de conservarlo

            if not taxes_unit:
                # si no hay unitarios, deja el price_unit igual al base
                line.price_unit = base
                continue

            # 4) calcular nuevo price_unit
            #    - porcentaje: multiplicativo (e.g., 12% y 5% => base * 1.12 * 1.05)
            #    - fijo: suma absoluta por unidad (amount)
            #    * Simplificación: ignoramos price_include/grupos para este caso mínimo.
            perc_factors = []
            fixed_sum = 0.0

            for t in taxes_unit:
                if t.amount_type == "percent":
                    perc_factors.append(1.0 + (t.amount or 0.0) / 100.0)
                elif t.amount_type == "fixed":
                    fixed_sum += (t.amount or 0.0)
                elif t.amount_type == "division":
                    # Si quisieras soportarlo: factor = 1 / (1 - amount/100)
                    if t.amount:
                        perc_factors.append(1.0 / (1.0 - (t.amount / 100.0)))
                # otros tipos (group/python) no se tratan en este mínimo

            factor = prod(perc_factors) if perc_factors else 1.0
            new_price = base * factor + fixed_sum

            # redondeo con la moneda del documento
            currency = line.move_id.currency_id or line.company_id.currency_id
            line.price_unit = currency.round(new_price)

    @api.onchange("price_unit")
    def _onchange_user_edit_price_unit(self):
        """
        Si el usuario edita manualmente price_unit y NO hay impuestos unitarios,
        actualiza la base. Si SÍ hay unitarios, asumimos que el usuario quiere
        fijar el final; opcionalmente podríamos recalcular la base inversa.
        """
        for line in self:
            if line.display_type:
                continue
            if not line.unit_price_tax_ids:
                # sin unitarios, la base sigue al price_unit
                line.price_unit_base = line.price_unit
            # Si hay unitarios y quieres mantener relación inversa:
            # else:
            #     # reconstruir base desde price_unit final (inverso del cálculo)
            #     perc_factors = ...
            #     line.price_unit_base = currency.round((line.price_unit - fixed_sum) / factor)

                