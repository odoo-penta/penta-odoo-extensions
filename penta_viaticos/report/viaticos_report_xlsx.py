from odoo import models


class ViaticosReportXlsx(models.AbstractModel):
    _name = "report.penta_viaticos.report_viaticos_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Reporte XLSX de Solicitud de Viaticos"

    def generate_xlsx_report(self, workbook, data, requests):
        sheet = workbook.add_worksheet("Viaticos")

        fmt_header = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#1E5DA3",
                "font_color": "#FFFFFF",
                "align": "center",
                "valign": "vcenter",
                "border": 1,
            }
        )
        fmt_text = workbook.add_format({"border": 1})
        fmt_date = workbook.add_format({"num_format": "yyyy-mm-dd", "border": 1})
        fmt_num = workbook.add_format({"num_format": "#,##0.00", "border": 1, "align": "right"})
        fmt_qty = workbook.add_format({"num_format": "#,##0.00", "border": 1, "align": "right"})

        columns = [
            ("Solicitud", 20),
            ("Solicitante", 28),
            ("Fecha solicitud", 14),
            ("Desde", 12),
            ("Hasta", 12),
            ("Ciudad origen", 18),
            ("Ciudad destino", 18),
            ("Producto", 28),
            ("Descripcion", 30),
            ("Cantidad", 10),
            ("Importe solicitado", 16),
            ("Total solicitado", 14),
            ("Importe permitido", 16),
            ("Total permitido", 14),
            ("Pagado por", 12),
        ]

        row = 0
        for col, (title, width) in enumerate(columns):
            sheet.set_column(col, col, width)
            sheet.write(row, col, title, fmt_header)
        row += 1

        for req in requests:
            detail_lines = req.product_line_ids
            if not detail_lines:
                self._write_no_detail_row(sheet, row, req, fmt_text, fmt_date)
                row += 1
                continue

            for line in detail_lines:
                sheet.write(row, 0, req.name or "", fmt_text)
                sheet.write(row, 1, req.request_owner_id.name or "", fmt_text)
                if req.create_date:
                    sheet.write_datetime(row, 2, req.create_date, fmt_date)
                else:
                    sheet.write(row, 2, "", fmt_text)

                if req.date_start:
                    sheet.write_datetime(row, 3, req.date_start, fmt_date)
                else:
                    sheet.write(row, 3, "", fmt_text)

                if req.date_end:
                    sheet.write_datetime(row, 4, req.date_end, fmt_date)
                else:
                    sheet.write(row, 4, "", fmt_text)

                sheet.write(row, 5, req.viaticos_city_origin_id.name or "", fmt_text)
                sheet.write(row, 6, req.viaticos_city_destination_id.name or "", fmt_text)
                sheet.write(row, 7, line.product_id.display_name or "", fmt_text)
                sheet.write(row, 8, line.description or "", fmt_text)
                sheet.write_number(row, 9, line.quantity or 0.0, fmt_qty)
                sheet.write_number(row, 10, line.viaticos_importe_solicitado or 0.0, fmt_num)
                sheet.write_number(row, 11, line.viaticos_total_solicitado or 0.0, fmt_num)
                sheet.write_number(row, 12, line.viaticos_importe_permitido or 0.0, fmt_num)
                sheet.write_number(row, 13, line.viaticos_total_permitido or 0.0, fmt_num)
                sheet.write(row, 14, self._label_paid_by(line.viaticos_paid_by), fmt_text)
                row += 1

    def _write_no_detail_row(self, sheet, row, req, fmt_text, fmt_date):
        sheet.write(row, 0, req.name or "", fmt_text)
        sheet.write(row, 1, req.request_owner_id.name or "", fmt_text)
        if req.create_date:
            sheet.write_datetime(row, 2, req.create_date, fmt_date)
        else:
            sheet.write(row, 2, "", fmt_text)

        if req.date_start:
            sheet.write_datetime(row, 3, req.date_start, fmt_date)
        else:
            sheet.write(row, 3, "", fmt_text)

        if req.date_end:
            sheet.write_datetime(row, 4, req.date_end, fmt_date)
        else:
            sheet.write(row, 4, "", fmt_text)

        sheet.write(row, 5, req.viaticos_city_origin_id.name or "", fmt_text)
        sheet.write(row, 6, req.viaticos_city_destination_id.name or "", fmt_text)
        sheet.write(row, 7, "Sin detalle", fmt_text)
        for col in range(8, 15):
            sheet.write(row, col, "", fmt_text)

    def _label_paid_by(self, paid_by):
        if paid_by == "employee":
            return "Empleado"
        if paid_by == "company":
            return "Empresa"
        return ""
