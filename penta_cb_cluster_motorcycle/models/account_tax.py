from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class AccountTax(models.Model):
    _inherit = "account.tax"

    apply_on_unit_price = fields.Boolean(
        string="Aplica sobre Precio Unitario?",
        help="Si está activo, el impuesto se calcula sobre price_unit."
    )

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        """
        Override REAL donde Odoo 18 calcula los impuestos.
        Aquí aplicamos tu lógica:
        - Si producto.is_ensabled = True
        - Y tax.apply_on_unit_price = True
        -> El ICE se calcula SIN descuento.
        """

        product = base_line.get("product_id")
        taxes = base_line.get("tax_ids")
        discount = base_line.get("discount", 0)
        price_unit = base_line.get("price_unit", 0)
        quantity = base_line.get("quantity", 1)

        # Llama a Odoo primero (para IVA, etc.)
        res = super()._add_tax_details_in_base_line(
            base_line, company, rounding_method=rounding_method
        )

        # Validación: no producto o no impuestos → no tocar
        if not product or not taxes:
            return res

        # Impuestos ICE
        ice_taxes = taxes.filtered(lambda t: t.apply_on_unit_price)

        if not (product.is_ensabled and ice_taxes):
            return res

        _logger.warning("🔥 RE-CALCULANDO ICE SIN DESCUENTO (override funcionando)")

        # BASE sin descuento (lo que tú necesitas)
        base_without_discount = price_unit * quantity

        # Recorremos los impuestos que ya calculó Odoo
        for tax_data in base_line["tax_details"]["taxes_data"]:
            tax = tax_data["tax"]

            if tax.apply_on_unit_price:
                _logger.warning("➡️ Base original Odoo (con descuento): %s", tax_data["raw_base_amount_currency"])
                _logger.warning("➡️ Base corregida SIN descuento: %s", base_without_discount)

                # Reemplazar base
                tax_data["raw_base_amount_currency"] = base_without_discount

                # Recalcular monto
                if tax.amount_type == "percent":
                    tax_data["raw_tax_amount_currency"] = base_without_discount * (tax.amount / 100)
                elif tax.amount_type == "fixed":
                    tax_data["raw_tax_amount_currency"] = tax.amount * quantity

                _logger.warning("🧾 ICE NUEVO = %s", tax_data["raw_tax_amount_currency"])

        return res