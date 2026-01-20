# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID  # no es estrictamente necesario en la versión con env
from odoo.api import Environment  # idem

def post_init_create_company_sequences(env):
    """
    Crea una secuencia por compañía para x.import si no existe.
    post_init_hook con firma de Odoo 18: recibe 'env'.
    """
    Seq = env["ir.sequence"].sudo()
    companies = env["res.company"].search([])

    for company in companies:
        exists = Seq.search([("code", "=", "x.import"), ("company_id", "=", company.id)], limit=1)
        if not exists:
            Seq.create({
                "name": f"Importación {company.name}",
                "code": "x.import",
                "prefix": "IG%(year)s-",
                "padding": 5,
                "implementation": "no_gap",
                "company_id": company.id,
            })
