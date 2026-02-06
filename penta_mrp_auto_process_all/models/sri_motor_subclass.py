# -*- coding: utf-8 -*-
from itertools import product
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

    product_tmpl_id = fields.Many2one("product.template", string="Producto", domain=[('is_ensabled', '=', True)])

    brand_name = fields.Many2one("product.brand", related="product_tmpl_id.product_brand_id", string="Marca")
    model_value_id = fields.Many2one("product.attribute.value", string="Modelo")
    year_value_id = fields.Many2one("product.attribute.value", string="Año", required=True)
    country_value_id = fields.Many2one("product.attribute.value", string="País de origen")
    class_value_id = fields.Many2one("product.attribute.value", string="Clase")
    type_value_id = fields.Many2one("product.attribute.value", string="Subclase")
    tonnage_value_id = fields.Many2one("product.attribute.value", string="Tonelaje")
    cylinder_value_id = fields.Many2one("product.attribute.value", string="Cilindraje")
    fuel_value_id = fields.Many2one("product.attribute.value", string="Combustible")
    bodywork_value_id = fields.Many2one("product.attribute.value", string="Carrocería")
    color_value_id = fields.Many2one("product.attribute.value", string="Color")
    weight_value_id = fields.Many2one("product.attribute.value", string="Carga Util")
    capacity_value_id = fields.Many2one("product.attribute.value", string="Capacidad Pasajeros")

    sri_value = fields.Monetary("Valor de avalúo")
    currency_id = fields.Many2one("res.currency", default=lambda s: s.env.company.currency_id.id)
    date_in = fields.Date("Fecha de ingreso")

    @api.constrains("subclass_subcategory_code", "subclass_code", "sri_id")
    def _check_numeric(self):
        for rec in self:
            for val in (rec.subclass_subcategory_code, rec.subclass_code, rec.sri_id):
                if val and not _only_digits(val):
                    raise models.ValidationError("Los campos de códigos SRI deben contener sólo números.")

    @api.onchange("product_tmpl_id")
    def _calculate_attributes(self):
        for rec in self:
            # Limpia primero
            rec.update({
                'model_value_id': False,
                'country_value_id': False,
                'class_value_id': False,
                'type_value_id': False,
                'tonnage_value_id': False,
                'cylinder_value_id': False,
                'fuel_value_id': False,
                'bodywork_value_id': False,
                'weight_value_id': False,
                'capacity_value_id': False,
            })

            if not rec.product_tmpl_id:
                return

            # Mapeo: nombre del atributo → campo en tu modelo
            attribute_map = {
                'MODELO': 'model_value_id',
                'PAÍS DE ORIGEN': 'country_value_id',
                'CLASE': 'class_value_id',
                'TIPO': 'type_value_id',
                'TONELAJE': 'tonnage_value_id',
                'CILINDRAJE': 'cylinder_value_id',
                'TIPO DE COMBUSTIBLE': 'fuel_value_id',
                'TIPO DE CARROCERIA': 'bodywork_value_id',
                'CARGA UTIL': 'weight_value_id',
                'NÚMERO DE PASAJEROS': 'capacity_value_id',
            }

            for line in rec.product_tmpl_id.attribute_line_ids:
                attr_name = line.attribute_id.name
                field_name = attribute_map.get(attr_name)

                if field_name and line.value_ids:
                    rec[field_name] = line.value_ids[0]

class ProductTemplate(models.Model):
    _inherit = "product.template"

    sri_motor_subclass_id = fields.Many2one("sri.motor.subclass", string="SRI Subclase (Motos)")
