# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ImportReportField(models.Model):
    _name = "penta.import.report.field"
    _description = "Campos parametrizables para reporte Excel de importaciones"
    _order = "sequence, id"

    name = fields.Char("Nombre de columna", required=True)
    technical_key = fields.Char("Clave técnica", required=True)
    model_name = fields.Char("Modelo origen", required=True)
    field_expr = fields.Char(
        "Expresión (dot-path)",
        required=True,
        help=(
            "Ruta desde alias: line (purchase.order.line), po (purchase.order), "
            "product (product.product), partner (proveedor), import_rec (x.import). "
            "Ej: import_rec.guide_bl"
        ),
    )
    compute_type = fields.Selection([
        ("expr", "Expresión directa"),
        ("method", "Método especial"),
    ], default="expr", required=True)
    method_name = fields.Char("Nombre del método (si compute_type='method')")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    @api.constrains("compute_type", "method_name", "field_expr")
    def _check_method(self):
        for rec in self:
            if rec.compute_type == "method" and not rec.method_name:
                raise models.ValidationError("Debes indicar 'method_name' si compute_type='method'.")
            if rec.compute_type == "expr" and not rec.field_expr:
                raise models.ValidationError("Debes indicar 'field_expr' si compute_type='expr'.")
