# -*- coding: utf-8 -*-
{
    "name": "Pentalab Account Validation",
    "summary": "Alerta por forma de pago SRI sin sistema financiero",
    "version": "18.0.1.0.0",
    "author": "PentaLab",
    "license": "LGPL-3",
    "category": "Accounting/Localizations",
    "depends": [
        "account",
        "l10n_ec_edi",
    ],
    "data": [
        "views/l10n_ec_sri_payment_views.xml",
        "data/l10n_ec_sri_payment_data.xml",
    ],
    "installable": True,
    "application": False,
}
