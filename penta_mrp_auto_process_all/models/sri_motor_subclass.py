# -*- coding: utf-8 -*-
from odoo import api, fields, models
import re


def _only_digits(val):
    return bool(re.fullmatch(r"\d+", (val or "").strip()))


class SriMotorSubclass(models.Model):
    _name = "sri.motor.subclass"
    _description = "SRI Subcategoría Subclase de Motos"
    _rec_name = "subclass_subcategory_code"
    _order = "create_date desc"

    subclass_subcategory_code = fields.Char("Código subclase subcategoría", required=True, help="Sólo números.")
    subclass_code = fields.Char("Código subclase", required=True, help="Sólo números.")
    sri_id = fields.Char("Id SRI-CAE", required=True, help="Sólo números.")

    brand_name = fields.Char(string="Marca") 
    model_value_id = fields.Many2one("product.attribute.value", string="Modelo")
    year_value_id = fields.Many2one("product.attribute.value", string="Año")
    country_value_id = fields.Many2one("product.attribute.value", string="País de origen")
    class_value_id = fields.Many2one("product.attribute.value", string="Clase")
    type_value_id = fields.Many2one("product.attribute.value", string="Tipo (Subclase)")
    tonnage_value_id = fields.Many2one("product.attribute.value", string="Tonelaje")

    sri_value = fields.Monetary("Valor de avalúo")
    currency_id = fields.Many2one("res.currency", default=lambda s: s.env.company.currency_id.id)
    date_in = fields.Date("Fecha de ingreso")

    @api.constrains("subclass_subcategory_code", "subclass_code", "sri_id")
    def _check_numeric(self):
        for rec in self:
            for val in (rec.subclass_subcategory_code, rec.subclass_code, rec.sri_id):
                if val and not _only_digits(val):
                    raise models.ValidationError("Los campos de códigos SRI deben contener sólo números.")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sri_motor_subclass_id = fields.Many2one("sri.motor.subclass", string="SRI Subclase (Motos)")
