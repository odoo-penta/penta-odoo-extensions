# -*- coding: utf-8 -*-
from odoo import fields, models


class StockProductionLot(models.Model):
    _inherit = "stock.lot"

    cpn = fields.Char(string="CPN", index=True, copy=False)
    pdi = fields.Char(string="PDI", index=True, copy=False)
    cpn_generated_at = fields.Datetime(string="Fecha/Hora gen. CPN", readonly=True, copy=False)
    pdi_generated_at = fields.Datetime(string="Fecha/Hora gen. PDI", readonly=True, copy=False)
    # ramv = fields.Char(string="RAMV / VIN", index=True)

    _sql_constraints = [
        ("uniq_cpn_company", "unique(company_id, cpn)", "El CPN debe ser único por compañía."),
        ("uniq_pdi_company", "unique(company_id, pdi)", "El PDI debe ser único por compañía."),
    ]
