# -*- coding: utf-8 -*-
from odoo.tools.misc import xlsxwriter


def get_xlsx_formats(workbook):
    """
    Devuelve un diccionario con formatos estándar para reportes XLSX
    """
    return {
        # Texto en negrita y centrado
        'bold_center': workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1}),
        # Texto en negrita
        'bold': workbook.add_format({'bold': True, 'border': 1}),
        # Solo borde (sin formato)
        'border': workbook.add_format({'border': 1}),
        # Centrado
        'center': workbook.add_format({'align': 'center', 'border': 1}),
        # Alineado a la derecha
        'right': workbook.add_format({'align': 'right', 'border': 1}),
        # Alineado a la izquierda
        'left': workbook.add_format({'align': 'left', 'border': 1}),
        # Numero con 2 decimales
        'number': workbook.add_format({'num_format': '#,##0.00', 'border': 1}),
        # Formato monetario con simbolo (USD)
        'currency': workbook.add_format({'num_format': '$#,##0.00', 'border': 1}),
        # Porcentajes
        'percent': workbook.add_format({'num_format': '0.00%', 'border': 1}),
        # Entero sin decimales
        'integer': workbook.add_format({'num_format': '#,##0', 'border': 1}),
        # Titulo grande centrado
        'title': workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 14}),
        # Encabezado con fondo gris
        'header_bg': workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#D9D9D9'}),
        # Fechas DD/MM/YYYY
        'date': workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1}),
        # Texto envuelto para celdas largas
        'wrap': workbook.add_format({'text_wrap': True, 'border': 1}),
        # Fondo de color (subtotales)
        'highlight': workbook.add_format({'bg_color': '#FFFF00', 'border': 1}),
        # Negrita con fondo azul (totales)
        'total': workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1}),
        # Numeros negativos en rojo
        'negative_number': workbook.add_format({'num_format': '#,##0.00;[Red]-#,##0.00', 'border': 1}),
    }
