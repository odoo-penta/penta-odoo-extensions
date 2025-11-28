# -*- coding: utf-8 -*-
from odoo import models
from odoo.addons.l10n_ec_edi.models import account_move


# 1) Agregar ICE como sub-tipo soportado
account_move.L10N_EC_VAT_SUBTAXES['ice'] = 3073

# 2) Agregar tarifa 3073 al listado de tarifas manejadas por EDI
account_move.L10N_EC_VAT_RATES[3073] = 5.0
