# -*- coding: utf-8 -*-
# Part of PentaLab. See LICENSE file for full copyright and licensing details.
# © 2025 PentaLab
# License Odoo Proprietary License v1.0 (https://www.odoo.com/documentation/user/16.0/legal/licenses/licenses.html#odoo-proprietary-license)

from odoo import models, fields,_

import base64
import io
from odoo.tools.misc import xlsxwriter
from odoo.addons.penta_base.reports.xlsx_formats import get_xlsx_formats
from odoo.tools import format_invoice_number
from openpyxl.utils import get_column_letter

class KardexWizard(models.TransientModel):
    _name = "project.wizard"
    _description = "Project Wizard"

    date_start = fields.Date(string='Start date')
    date_end = fields.Date(string='End Date')

    
    # === FUNCIÓN PRINCIPAL DE XLS ===
    def print_report_xls(self, report_lines=None):
        if report_lines is None:
            data = {
                'form': self.read(['date_start', 'date_end'])[0]
            }
            obj_report = self.env['report.project.report']
            report_lines = obj_report.get_project(data.get('form', {})) or []
        report = self.generate_xlsx_report(report_lines)
        today = fields.Date.context_today(self)
        file_name = f"Project_{today.strftime('%d_%m_%Y')}.xlsx"
        attachment = self.env["ir.attachment"].create({
            'name': file_name,
            'type': "binary",
            'datas': base64.b64encode(report),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            'type': "ir.actions.act_url",
            'url': f"/web/content/{attachment.id}?download=true",
            'target': "self",
        }
    
    # === GENERAR ARCHIVO XLSX ===
    def generate_xlsx_report(self, report_lines):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Project')

        # Formatos estándar (usa tu helper de penta_base)
        formats = get_xlsx_formats(workbook)

        # === ENCABEZADO GENERAL ===
        worksheet.write("A1", self.env.company.display_name, formats["title"])
        worksheet.write("A2", _('Date From:'), formats["bold"])
        worksheet.write("B2", self.date_start.strftime("%d/%m/%Y"))
        worksheet.write("A3", _('Date Until:'), formats["bold"])
        worksheet.write("B3", self.date_end.strftime("%d/%m/%Y"))
        worksheet.write("C2", _('Print Date:'), formats["bold"])
        worksheet.write("D2", fields.Date.context_today(self).strftime("%d/%m/%Y"),formats["date"])
        worksheet.write("A4", _('User:'), formats["bold"])
        worksheet.write("B4", self.env.user.name)

        # === ENCABEZADOS DE COLUMNA ===
        headers = [
            "ID",
            _('Create on'),
            _('Assignment Date'),
            _('Effective date'),
            _('Completion date'),
            _('Length of stay in days'),
            _('Effective Hours'),
            _('Work order status'),
            _('Mechanic'),
            _('Under warranty'),
            _('Identification number'),
            _('Customer'),
            _('Customer category'),
            _('Chasis'),
            _('Engine'),
            _('Plate'),
            _('Product (Internal Reference)'),
            _('Product (header)'),
            _('Model'),
            _('Brand'),
            _('Line (Product category)'),
            _('Product category'),
            _('Product subcategory'),
            _('Internal reference'),
            _('Product (Sales Order)'),
            _('Quantity'),
            _('Unit Price'),
            _('Discount'),
            _('Net Amount'),
            _('Invoice Status'),
            _('Invoice'),   
            _('Invoice Date'),
            _('Almacen'),
            _('Tèrmino de pago'),
        ]

        worksheet.set_row(10, 20)
        for col, header in enumerate(headers):
            worksheet.write(6, col, header, formats["header_bg"])

        # === LLENAR DATOS EN FILAS ===
        row = 7
        for line in report_lines:
            worksheet.write(row, 0, line.get('task_id', ''))
            worksheet.write(row, 1, line.get('created_on', ''))
            worksheet.write(row, 2, line.get('date_assign', ''))
            worksheet.write(row, 3, line.get('effective_date', ''))
            worksheet.write(row, 4, line.get('date_end', ''))
            worksheet.write(row, 5, line.get('dispatch_date', '')) # Tiempo permanecencia en dias  este campo es calculado
            worksheet.write(row, 6, line.get('effective_hours', 0))
            worksheet.write(row, 7, line.get('stage_id', ''))
            worksheet.write(row, 8, line.get('user_ids', ''))
            worksheet.write(row, 9, 'Sí' if line.get('under_warranty') else 'No')
            worksheet.write(row, 10, line.get('partner_vat', ''))
            worksheet.write(row, 11, line.get('partner_name', ''))
            worksheet.write(row, 12, line.get('customer_category', ''))
            worksheet.write(row, 13, line.get('chassis', ''))
            worksheet.write(row, 14, line.get('motor_number', ''))
            worksheet.write(row, 15, line.get('placa', ''))
            worksheet.write(row, 16, line.get('ref_int_product_name', ''))
            worksheet.write(row, 17, line.get('product_name', ''))
            worksheet.write(row, 18, line.get('model', ''))
            worksheet.write(row, 19, line.get('brand', ''))
            worksheet.write(row, 20, line.get('line_category', ''))
            worksheet.write(row, 21, line.get('product_category', ''))
            worksheet.write(row, 22, line.get('product_subcategory', ''))
            worksheet.write(row, 23, line.get('internal_reference', ''))
            worksheet.write(row, 24, line.get('sale_product_name', ''))
            worksheet.write(row, 25, line.get('quantity', 0))
            worksheet.write(row, 26, line.get('unit_price', 0))
            worksheet.write(row, 27, line.get('discount', 0))
            worksheet.write(row, 28, line.get('net_amount', 0))
            worksheet.write(row, 29, line.get('invoice_status', ''))
            worksheet.write(row, 30, line.get('invoice_name', ''))
            worksheet.write(row, 31, line.get('invoice_date', ''))
            worksheet.write(row, 32, line.get('warehouse', ''))
            worksheet.write(row, 33, line.get('payment_term', ''))
            row += 1

        column_widths = [12, 15, 15, 12, 20, 15, 12, 15, 20, 20, 
                     15, 15, 15, 20, 15, 15, 20, 20, 20, 15,
                     20, 10, 12, 10, 12, 15, 15, 12, 15, 15, 15, 12]
    
        for col, width in enumerate(column_widths):
            worksheet.set_column(col, col, width)

        workbook.close()
        output.seek(0)
        return output.read()

    def check_report(self):
        """Report type selection logic"""
        # Armamos los datos base
        data = {
            'form': self.read([
                'date_start',
                'date_end',
            ])[0]
        }

        obj_report = self.env['report.project.report']
        report_lines = obj_report.get_project(data.get('form', {}))
        return self.print_report_xls(report_lines)
      