# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ImportBoarding(models.Model):
    """
    Catálogo de puertos / ciudades de embarque
    """
    _name = "import.boarding"
    _description = "Puerto / Ciudad de Embarque"
    _order = "name"
    _sql_constraints = [
        ("code_unique", "unique(code)", _("El código de puerto/ciudad debe ser único."))
    ]

    code = fields.Char(
        string="Código de Puerto / Ciudad",
        required=True,
        index=True,
        size=10,
        help="Código interno o internacional del puerto o ciudad de embarque.",
    )

    name = fields.Char(
        string="Puerto / Ciudad",
        required=True,
        translate=True,
    )

    country_id = fields.Many2one(
        "res.country",
        string="País",
        required=True,
        index=True,
    )  
            
    def name_get(self):
        """Mostrar: CODE - NAME - PAÍS en todos los Many2one."""
        res = []
        for rec in self:
            code = rec.code or ''
            nm = rec.name or ''
            country = rec.country_id.name or ''
            res.append((rec.id, f"{code} - {nm} - {country}"))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permitir buscar por código, nombre o país."""
        args = args or []
        domain = ['|', '|',
                  ('code', operator, name),
                  ('name', operator, name),
                  ('country_id.name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()