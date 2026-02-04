from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_bancarizacion_warning_message(self):
        self.ensure_one()
        threshold = self.l10n_ec_sri_payment_id.minimum_amount
        payment_name = self.l10n_ec_sri_payment_id.display_name
        return _(
            "Para facturas de venta o compra con total igual o mayor a %(threshold).2f, "
            "no se recomienda usar la forma de pago SRI '%(payment)s'. "
            "Seleccione una opcion que implique bancarizacion."
        ) % {
            "threshold": threshold,
            "payment": payment_name,
        }

    def _requires_bancarizacion_alert(self):
        self.ensure_one()
        if self.move_type not in ("out_invoice", "in_invoice"):
            return False
        if not self.l10n_ec_sri_payment_id:
            return False

        sri_payment = self.l10n_ec_sri_payment_id
        if not sri_payment.validate_minimum_amount:
            return False

        threshold = sri_payment.minimum_amount or 0.0
        if threshold <= 0.0:
            return False

        total = abs(self.amount_total)
        return float_compare(total, threshold, precision_rounding=self.currency_id.rounding) >= 0

    @api.onchange("l10n_ec_sri_payment_id", "amount_total", "currency_id", "move_type")
    def _onchange_l10n_ec_sri_payment_bancarizacion(self):
        self.ensure_one()
        if not self._requires_bancarizacion_alert():
            return

        return {
            "warning": {
                "title": _("Alerta de bancarizacion"),
                "message": self._get_bancarizacion_warning_message(),
            }
        }

    def action_post(self):
        for move in self:
            if move._requires_bancarizacion_alert():
                raise UserError(move._get_bancarizacion_warning_message())
        return super().action_post()
