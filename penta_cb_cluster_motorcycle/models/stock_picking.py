# -*- coding: utf-8 -*-
from odoo import models, fields
import base64
import io
from odoo.tools.misc import xlsxwriter
from odoo.addons.penta_base.reports.xlsx_formats import get_xlsx_formats

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    def print_report(self):
        report = self.generate_xlsx_report()
        file_name = f"{self.name}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(report),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
    
    def generate_xlsx_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("products")
        # Formatos
        formats = get_xlsx_formats(workbook)
        # Ancho de columnas
        worksheet.set_column('A:A', 24)
        worksheet.set_column('B:E', 48)
        # Encabezados
        headers = ['REFERENCIA INTERNA', 'PRODUCTO', 'NÚMERO DE SERIE/LOTE/CHASIS', 'NÚMERO DE MOTOR', 'RAMV']
        row = 0
        # Mapear titulos
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, formats['header_bg'])
        row += 1
        # Mapear datos
        for line in self.move_ids_without_package:
            for move_line in line.move_line_ids:
                worksheet.write(row, 0, line.product_id.default_code or '', formats['border'])
                worksheet.write(row, 1, line.product_id.name or '', formats['border'])
                worksheet.write(row, 2, move_line.lot_name or '', formats['border'])
                worksheet.write(row, 3, move_line.motor_number or '', formats['border'])
                worksheet.write(row, 4, move_line.ramv or '', formats['border'])
                row += 1
        workbook.close()
        output.seek(0)
        return output.read()
