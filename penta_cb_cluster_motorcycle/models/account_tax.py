from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = "account.tax"

    apply_on_unit_price = fields.Boolean(
        string="Aplica sobre Precio Unitario?",
        help="Si está activo, el impuesto (ICE) se calcula sobre price_unit sin descuento."
    )

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        """
        OVERRIDE :
        ------------------
        Este método reemplaza completamente
        la base del ICE y rehace la base del IVA.

        Lógica implementada:
        ✓ ICE SIN descuento
        ✓ IVA sobre:
            base_con_descuento + ICE_sin_descuento
        """

        res = super()._add_tax_details_in_base_line(base_line, company, rounding_method=rounding_method)

        product = base_line.get("product_id")
        taxes = base_line.get("tax_ids")
        discount = base_line.get("discount", 0)
        price_unit = base_line.get("price_unit", 0)
        quantity = base_line.get("quantity", 1)

        if not product or not taxes:
            return res

        # Filtrar impuestos ICE
        ice_taxes = taxes.filtered(lambda t: t.apply_on_unit_price)

        # Si no aplica lógica ICE personalizada, salimos
        if not (product.is_ensabled and ice_taxes):
            return res


        base_with_discount = price_unit * quantity * (1 - discount / 100)
        base_without_discount = price_unit * quantity  # ICE correcto


        new_ice_amount = 0

        for tax_data in base_line["tax_details"]["taxes_data"]:
            tax = tax_data["tax"]
            if tax.apply_on_unit_price:
                # Cambiamos la base
                tax_data["raw_base_amount_currency"] = base_without_discount
                tax_data["raw_base_amount"] = base_without_discount

                # Recalcular monto ICE
                if tax.amount_type == "percent":
                    tax_data["raw_tax_amount_currency"] = base_without_discount * (tax.amount / 100)
                    tax_data["raw_tax_amount"] = base_without_discount * (tax.amount / 100)
                elif tax.amount_type == "fixed":
                    tax_data["raw_tax_amount_currency"] = tax.amount * quantity

                new_ice_amount += tax_data["raw_tax_amount_currency"]

        iva_taxes = taxes.filtered(lambda t: not t.apply_on_unit_price)

        base_iva = base_with_discount + new_ice_amount


        for tax_data in base_line["tax_details"]["taxes_data"]:
            tax = tax_data["tax"]

            # Solo impuestos que NO son ICE
            if tax in iva_taxes:
                tax_data["raw_base_amount_currency"] = base_iva
                tax_data["raw_base_amount"] = base_iva

                if tax.amount_type == "percent":
                    tax_data["raw_tax_amount_currency"] = base_iva * (tax.amount / 100)
                    tax_data["raw_tax_amount"] = base_iva * (tax.amount / 100)
                elif tax.amount_type == "fixed":
                    tax_data["raw_tax_amount_currency"] = tax.amount * quantity
                    tax_data["raw_tax_amount"] = tax.amount * quantity

        return res
