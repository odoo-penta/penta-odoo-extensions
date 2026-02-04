from odoo import fields, models


class L10nEcSriPayment(models.Model):
    _inherit = "l10n_ec.sri.payment"

    validate_minimum_amount = fields.Boolean(
        string="Validar monto minimo",
        help="Muestra alerta en factura cuando el total alcanza el monto configurado.",
    )
    minimum_amount = fields.Float(
        string="Monto",
        digits="Account",
        default=0.0,
    )

