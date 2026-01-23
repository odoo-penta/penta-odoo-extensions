# -*- coding: utf-8 -*-
# Part of PentaLab. See LICENSE file for full copyright and licensing details.
# © 2025 PentaLab
# License Odoo Proprietary License v1.0 (https://www.odoo.com/documentation/user/16.0/legal/licenses/licenses.html#odoo-proprietary-license)

from odoo import models, fields, api

import base64
import io
from odoo.tools.misc import xlsxwriter
from odoo.addons.penta_base.reports.xlsx_formats import get_xlsx_formats
from odoo.tools import format_invoice_number
from openpyxl.utils import get_column_letter

class KardexWizard(models.TransientModel):
    _name = "kardex.wizard"
    _description = "Kardex Wizard"

    date_start = fields.Date()
    date_end = fields.Date()
    date_print = fields.Date()
    product_id = fields.Many2one("product.template", string="Producto")
    warehouse_id = fields.Many2one('stock.warehouse', string="Almacén")
    location_id = fields.Many2one('stock.location', string="Ubicación", domain=[('usage', '=', 'internal')])

    def _print_report(self, data):
        data["form"].update(
            self.read([
                "date_start",
                "date_end",
                "product_id",
                "warehouse_id",
            ])[0]
        )
        return self.env.ref("penta_kardex.action_kardex_report").report_action(
            self, data=data, config=False
        )

    
    # === FUNCIÓN PRINCIPAL DE XLS ===
    def print_report_xls(self, report_lines):
        report = self.generate_xlsx_report(report_lines)
        today = fields.Date.context_today(self)
        file_name = f"Kardex_{today.strftime('%d_%m_%Y')}.xlsx"
        attachment = self.env["ir.attachment"].create({
            "name": file_name,
            "type": "binary",
            "datas": base64.b64encode(report),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
    
    # === GENERAR ARCHIVO XLSX ===
    def generate_xlsx_report(self, report_lines):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Kardex")

        # Formatos estándar (usa tu helper de penta_base)
        formats = get_xlsx_formats(workbook)

        # Obtener la precisión decimal definida en Odoo
        price_precision = self.env['decimal.precision'].precision_get('Product Price')

        # Crear el formato numérico dinámicamente, por ejemplo: "#,##0.00" o "#,##0.000000"
        num_format = '#,##0.' + ('0' * price_precision)

        # Crear el formato de celda en Excel
        format_decimalized_amount = workbook.add_format({
            'num_format': num_format,
            'border': 1,
            'align': 'right'
        })

        # === ENCABEZADO GENERAL ===
        worksheet.write("A1", self.env.company.display_name, formats["title"])
        worksheet.write("A2", "Fecha Desde:", formats["bold"])
        worksheet.write("B2", self.date_start.strftime("%d/%m/%Y"))
        worksheet.write("A3", "Fecha Hasta:", formats["bold"])
        worksheet.write("B3", self.date_end.strftime("%d/%m/%Y"))
        worksheet.write("C2", "Fecha de Impresión:", formats["bold"])
        worksheet.write("E2", fields.Date.context_today(self).strftime("%d/%m/%Y"),formats["date"])
        worksheet.write("A4", "Usuario:", formats["bold"])
        worksheet.write("B4", self.env.user.name)
        worksheet.write("A5", "Categoría Principal:", formats["bold"])
        worksheet.write("B5", self.product_id.categ_id.name or "")
        worksheet.write("A6", "Producto:", formats["bold"])
        worksheet.write("B6", self.product_id.display_name or "")
        worksheet.write("A7", "Referencia Interna:", formats["bold"])
        worksheet.write("B7", self.product_id.default_code or "")
        worksheet.write("A8", "Almacén:", formats["bold"])
        worksheet.write("B8", self.warehouse_id.name or "")

        # === ENCABEZADOS DE COLUMNA ===
        headers = [
            "Fecha",
            "Tipo de Movimiento",
            "Referencia",
            "Comprobante",
            "Cantidad Entrada",
            "Costo Unitario Entrada",
            "Costo Total Entrada",
            "Cantidad Salida",
            "Costo Unitario Salida",
            "Costo Total Salida",
            "Cantidad Saldo",
            "Costo Unitario Promedio",
            "Costo Total Saldo",
        ]

        worksheet.set_row(10, 20)
        for col, header in enumerate(headers):
            worksheet.write(10, col, header, formats["header_bg"])

        # === LLENAR DATOS EN FILAS ===
        row = 11
        for line in report_lines:
            worksheet.write(row, 0, line["date"], formats["border"])
            worksheet.write(row, 1, line["type"], formats["border"])
            worksheet.write(row, 2, line["reference"], formats["border"])
            worksheet.write(row, 3, line["voucher"], formats["border"])
            worksheet.write(row, 4, line["qty_in"], format_decimalized_amount)
            worksheet.write(row, 5, line["cost_in_unit"], format_decimalized_amount)
            worksheet.write(row, 6, line["cost_in_total"], format_decimalized_amount)
            worksheet.write(row, 7, line["qty_out"], format_decimalized_amount)
            worksheet.write(row, 8, line["cost_out_unit"], format_decimalized_amount)
            worksheet.write(row, 9, line["cost_out_total"], format_decimalized_amount)
            worksheet.write(row, 10, line["qty_balance"], format_decimalized_amount)
            worksheet.write(row, 11, line["cost_avg_unit"], format_decimalized_amount)
            worksheet.write(row, 12, line["cost_total_balance"], format_decimalized_amount)
            row += 1

        # === AJUSTE DE ANCHOS DE COLUMNA ===
        worksheet.set_column("A:A", 12)
        worksheet.set_column("B:B", 25)
        worksheet.set_column("C:D", 20)
        worksheet.set_column("E:M", 18)

        workbook.close()
        output.seek(0)
        return output.read()

    def check_report(self):
        """Lógica de selección del tipo de reporte"""
        # Armamos los datos base
        data = {
            "form": self.read([
                "date_start",
                "date_end",
                "product_id",
                "warehouse_id",
                "location_id"
            ])[0]
        }

        # Si el usuario seleccionó 'excel'
        if self._context.get("report_type") == "excel":
            # Obtenemos los datos del reporte XLSX
            obj_report = self.env["report.penta_kardex.kardex_report"]
            report_lines = obj_report.get_kardex(data.get("form", {}))
            return self.print_report_xls(report_lines)
        else:
            # Por defecto imprime PDF o vista normal
            return self._print_report(data)
