from odoo import models, fields, api
import xml.etree.ElementTree as ET
from odoo.exceptions import UserError
import base64
import re
import csv
import io
import requests
from datetime import datetime, time
import pytz

class popup(models.TransientModel):
    _name = 'popup'
    _description = 'Popup Wizard'

    archivo = fields.Binary(string='Archivo', required=False)

    def action_confirm(self):
        if self.archivo:
            archivo_decodificado = self.decode_file(self.archivo)
            registros = self.read_csv_content(archivo_decodificado)
            # Define el formato de fecha esperado
            input_date_format_full = '%d/%m/%Y %H:%M:%S'
            input_date_format_date_only = '%d/%m/%Y'
            output_date_format = '%Y-%m-%d %H:%M:%S'
            facturas_duplicadas = []
            ruc_empresa = self.env.company.vat  # Obtener el RUC de la empresa actual

            for registro in registros:
                identificacion_receptor = registro.get('IDENTIFICACION_RECEPTOR', '')
                # Validar si el receptor coincide con el RUC de la empresa
                if identificacion_receptor != ruc_empresa:
                    continue  # Saltar este registro
                encontrado = self.env['archivo.model'].search([('clave_acceso', '=', registro.get('CLAVE_ACCESO', ''))])

                if not encontrado:
                    user_tz = pytz.timezone(self.env.user.tz or 'UTC')
                    if registro.get('FECHA_EMISION'):
                        if len(registro['FECHA_EMISION']) > 10:
                            dt = datetime.strptime(registro['FECHA_EMISION'], input_date_format_full)
                        else:
                            dt = datetime.strptime(registro['FECHA_EMISION'], input_date_format_date_only)
                            dt = datetime.combine(dt.date(), time(0, 0))  # si viene sin hora -> medianoche local

                        # Localizar y pasar a UTC
                        local_dt = user_tz.localize(dt)
                        fecha_emision = fields.Datetime.to_string(local_dt.astimezone(pytz.UTC))
                    self.env['archivo.model'].create({
                        'fecha_subida': fields.Datetime.now(),
                        'xml_file': None,
                        'company_id': self.env.company.id,
                        'xml_filename': 'archivo.xml',
                        'clave_acceso': registro.get('CLAVE_ACCESO', ''),
                        'numero_factura': f"Fact {registro.get('SERIE_COMPROBANTE')}" if registro.get('TIPO_COMPROBANTE') == 'Factura' else f"Ret {registro.get('SERIE_COMPROBANTE')}",
                        'serie_comprobante': registro.get('SERIE_COMPROBANTE', ''),
                        'fecha_autorizacion': (
                            fields.Datetime.to_string(
                                pytz.timezone(self.env.user.tz or 'America/Guayaquil')
                                .localize(
                                    datetime.strptime(registro.get('FECHA_AUTORIZACION', ''), input_date_format_full)
                                    if registro.get('FECHA_AUTORIZACION') and len(registro.get('FECHA_AUTORIZACION')) > 10
                                    else datetime.strptime(registro.get('FECHA_AUTORIZACION', ''), input_date_format_date_only)
                                )
                                .astimezone(pytz.UTC)
                            )
                        ) if registro.get('FECHA_AUTORIZACION') else False,
                        'fecha_emision': fecha_emision,
                        'identificacion_receptor': registro.get('IDENTIFICACION_RECEPTOR', ''),
                        'identificacion_emisor': registro.get('RUC_EMISOR', ''),
                        'valor_sin_impuestos': registro.get('VALOR_SIN_IMPUESTOS', 0.0),
                        'iva': registro.get('IVA', 0.0),
                        'importe_total': registro.get('IMPORTE_TOTAL', 0.0),
                        'numero_documento_modificado': registro.get('NUMERO_DOCUMENTO_MODIFICADO', ''),
                        'name_emisor': registro.get('RAZON_SOCIAL_EMISOR', ''),
                        'type_doc': registro.get('TIPO_COMPROBANTE', ''),
                    })

            action = self.env['ir.actions.actions'].sudo().search([('name', '=', '{"en_US": "Imports"}')], limit=1)
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'action': action.id,
                },
            }
        return False
    
    def decode_file(self, archivo):
        try:
            return base64.b64decode(archivo).decode('utf-8')
        except UnicodeDecodeError:
            return base64.b64decode(archivo).decode('iso-8859-1')
        
    
    def read_csv_content(self, archivo_decodificado):
        archivo_csv = io.StringIO(archivo_decodificado)
        reader = csv.DictReader(archivo_csv, delimiter='\t')
        return list(reader)