from odoo import models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_amount(self):
        super()._compute_amount()
        for line in self:
            if not line.product_id or not line.product_id.is_ensabled:
                continue
            ice_taxes = line.tax_id.filtered(lambda t: t.apply_on_unit_price)
            if not ice_taxes:
                continue
            ice_total = 0
            for tax in ice_taxes:
                if tax.amount_type == "percent":
                    ice_total += (tax.amount / 100.0) * line.price_unit
                else:
                    ice_total += tax.amount
            native = line.tax_id - ice_taxes
            native_res = native.compute_all(
                line.price_unit,
                line.order_id.currency_id,
                line.product_uom_qty,
                product=line.product_id,
                partner=line.order_id.partner_id
            )
            line.price_tax = (native_res["total_included"] - native_res["total_excluded"]) + ice_total
            line.price_total = native_res["total_excluded"] + ice_total
            line.price_subtotal = native_res["total_excluded"]
