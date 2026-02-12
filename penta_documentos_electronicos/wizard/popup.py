from odoo import models, fields
from odoo.exceptions import UserError
import base64
import csv
import io
from datetime import datetime, time
import pytz
import xml.etree.ElementTree as ET


class Popup(models.TransientModel):
    _name = 'popup'
    _description = 'Popup Wizard Importación'

    archivo = fields.Binary(string='Archivo', required=True)
    archivo_nombre = fields.Char(string='Nombre del archivo')

    # --------------------------------------------------
    # ACCIÓN PRINCIPAL
    # --------------------------------------------------

    def action_confirm(self):
        if not self.archivo:
            raise UserError("Debe subir un archivo.")

        filename = (self.archivo_nombre or '').lower()

        if filename.endswith('.xml'):
            return self._importar_xml(base64.b64decode(self.archivo))

        return self._importar_csv()

    # --------------------------------------------------
    # CSV
    # --------------------------------------------------

    def _importar_csv(self):
        contenido = self._decode_file(self.archivo)
        registros = self._read_csv(contenido)

        if not registros:
            raise UserError("El archivo no contiene registros válidos.")

        ruc_empresa = self.env.company.vat
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')

        claves = [r.get('CLAVE_ACCESO') for r in registros if r.get('CLAVE_ACCESO')]
        existentes = set(
            self.env['archivo.model']
            .search([('clave_acceso', 'in', claves)])
            .mapped('clave_acceso')
        )

        creados = 0
        ignorados = 0

        for r in registros:
            if r.get('IDENTIFICACION_RECEPTOR') != ruc_empresa:
                ignorados += 1
                continue

            clave = r.get('CLAVE_ACCESO')
            if not clave or clave in existentes:
                ignorados += 1
                continue

            vals = self._prepare_vals_from_csv(r, user_tz)

            if not vals:
                ignorados += 1
                continue

            self.env['archivo.model'].create(vals)
            existentes.add(clave)
            creados += 1

        return self._notify(creados, ignorados)

    # --------------------------------------------------
    # XML
    # --------------------------------------------------

    def _importar_xml(self, xml_bytes):
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError:
            raise UserError("El XML no es válido.")

        info_tributaria = root.find('infoTributaria')

        if root.tag == 'comprobanteRetencion':
            info_ret = root.find('infoCompRetencion')

            clave = info_tributaria.findtext('claveAcceso')

            if self.env['archivo.model'].search([('clave_acceso', '=', clave)], limit=1):
                raise UserError("Este comprobante ya fue importado.")

            fecha_emision = self._parse_fecha(info_ret.findtext('fechaEmision'))

            num_serie = (
                (info_tributaria.findtext('estab') or '') +
                (info_tributaria.findtext('ptoEmi') or '') +
                (info_tributaria.findtext('secuencial') or '')
            )

            num_serie_formateado = self._format_num_doc_sustento(num_serie)
            partner = self.env['res.partner'].search([('vat', '=', info_tributaria.findtext('ruc'))], limit=1)

            archivo = self.env['archivo.model'].create({
                'clave_acceso': clave,
                'type_doc': 'Comprobante de Retención',
                'serie_comprobante': num_serie_formateado,
                'numero_factura': f"RET-{num_serie_formateado}",
                'fecha_emision': fecha_emision,
                'identificacion_emisor': info_tributaria.findtext('ruc'),
                'identificacion_receptor': info_ret.findtext('identificacionSujetoRetenido'),
                'name_emisor': info_tributaria.findtext('razonSocial'),
                'xml_file': base64.b64encode(xml_bytes),
                'xml_filename': self.archivo_nombre,
                'state': 'importado',
                'bank_withholding': bool(partner and partner.bank_withholding_agent),
            })

            self._crear_lineas_retencion(root, archivo)
            archivo.state = 'descargado'
        elif root.tag == 'factura':
            info_fac = root.find('infoFactura')

            clave = info_tributaria.findtext('claveAcceso')

            if self.env['archivo.model'].search([('clave_acceso', '=', clave)], limit=1):
                raise UserError("Este comprobante ya fue importado.")

            # Fecha emisión
            fecha_emision = self._parse_fecha(info_fac.findtext('fechaEmision'))

            # Número de serie
            num_serie = (
                (info_tributaria.findtext('estab') or '') +
                (info_tributaria.findtext('ptoEmi') or '') +
                (info_tributaria.findtext('secuencial') or '')
            )
            num_serie_formateado = self._format_num_doc_sustento(num_serie)

            # ==========================
            # VALORES ECONÓMICOS
            # ==========================
            base_iva = 0.0
            valor_iva = 0.0

            total_con_impuestos = info_fac.find('totalConImpuestos')
            if total_con_impuestos is not None:
                for imp in total_con_impuestos.findall('totalImpuesto'):
                    if imp.findtext('codigo') == '2':  # IVA
                        base_iva += float(imp.findtext('baseImponible', '0') or 0)
                        valor_iva += float(imp.findtext('valor', '0') or 0)

            importe_total = float(info_fac.findtext('importeTotal', '0') or 0)

            # ==========================
            # CREACIÓN DEL REGISTRO
            # ==========================
            archivo = self.env['archivo.model'].create({
                'clave_acceso': clave,
                'type_doc': 'Factura',
                'numero_factura': f"FAC-{num_serie_formateado}",
                'serie_comprobante': num_serie_formateado,
                'fecha_emision': fecha_emision,
                'identificacion_emisor': info_tributaria.findtext('ruc'),
                'name_emisor': info_tributaria.findtext('razonSocial'),
                'xml_file': base64.b64encode(xml_bytes),
                'xml_filename': self.archivo_nombre,
                'state': 'importado',

                'valor_sin_impuestos': base_iva,
                'iva': valor_iva,
                'importe_total': importe_total,
            })

            # Líneas de la factura
            self._crear_lineas_factura(root, archivo)
            archivo.state = 'descargado'

        return self._notify(1, 0)

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    def _prepare_vals_from_csv(self, r, user_tz):
        tipo = r.get('TIPO_COMPROBANTE')

        if tipo not in ('Factura', 'Comprobante de Retención'):
            return False

        partner = self.env['res.partner'].search(
            [('vat', '=', r.get('RUC_EMISOR'))], limit=1
        )

        vals = {
            'fecha_subida': fields.Datetime.now(),
            'company_id': self.env.company.id,
            'clave_acceso': r.get('CLAVE_ACCESO'),
            'serie_comprobante': r.get('SERIE_COMPROBANTE', ''),
            'fecha_emision': self._parse_fecha(r.get('FECHA_EMISION'), user_tz),
            'fecha_autorizacion': self._parse_fecha(r.get('FECHA_AUTORIZACION'), user_tz),
            'identificacion_receptor': r.get('IDENTIFICACION_RECEPTOR', ''),
            'identificacion_emisor': r.get('RUC_EMISOR', ''),
            'valor_sin_impuestos': float(r.get('VALOR_SIN_IMPUESTOS') or 0),
            'iva': float(r.get('IVA') or 0),
            'importe_total': float(r.get('IMPORTE_TOTAL') or 0),
            'numero_documento_modificado': r.get('NUMERO_DOCUMENTO_MODIFICADO', ''),
            'name_emisor': r.get('RAZON_SOCIAL_EMISOR', ''),
            'type_doc': tipo,
        }

        if tipo == 'Factura':
            vals['numero_factura'] = f"FAC-{vals['serie_comprobante']}"

        else:
            vals['numero_factura'] = f"RET-{vals['serie_comprobante']}"
            vals['bank_withholding'] = bool(
                partner and partner.bank_withholding_agent
            )

        return vals

    def _parse_fecha(self, fecha_str, tz=None):
        if not fecha_str:
            return False

        fmt = '%d/%m/%Y %H:%M:%S' if len(fecha_str) > 10 else '%d/%m/%Y'
        dt = datetime.strptime(fecha_str, fmt)

        if len(fecha_str) <= 10:
            dt = datetime.combine(dt.date(), time.min)

        tz = tz or pytz.UTC
        return fields.Datetime.to_string(
            tz.localize(dt).astimezone(pytz.UTC)
        )

    def _format_num_doc_sustento(self, num):
        num = (num or '').strip()

        # Solo números
        num = ''.join(filter(str.isdigit, num))

        if len(num) < 7:
            return num  # no es válido, devuélvelo igual

        establecimiento = num[:3]
        punto_emision = num[3:6]
        secuencial = num[6:]

        return f"{establecimiento}-{punto_emision}-{secuencial}"

    def _decode_file(self, archivo):
        try:
            return base64.b64decode(archivo).decode('utf-8')
        except UnicodeDecodeError:
            return base64.b64decode(archivo).decode('iso-8859-1')

    def _read_csv(self, contenido):
        return list(csv.DictReader(io.StringIO(contenido), delimiter='\t'))

    def _notify(self, creados, ignorados):
        tipo = 'success' if creados else 'warning'
        mensaje = f'Importación: {creados} creados, {ignorados} ignorados.'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': mensaje,
                'type': tipo,
            },
            'effect': creados and {
                'type': 'rainbow_man',
                'message': 'Importación finalizada 🎉',
            } or False
        }


    def _crear_lineas_factura(self, root, archivo):
        etiquetas = [
            det.find('descripcion').text.strip()
            for det in root.findall('.//detalle')
            if det.find('descripcion') is not None
        ]

        # Construimos una tabla simple con dos columnas
        table_html  = "<table class='table table-sm o_table' style='width:100%;'>"
        table_html += "<thead><tr><th>Etiqueta XML</th><th>Producto Odoo</th></tr></thead><tbody>"

        for etiqueta in etiquetas:
            # Buscar producto en homologación
            homolog = self.env['product.homologation'].search(
                [('etiqueta', '=', etiqueta)], limit=1
            )
            if homolog and homolog.product_variant_id:
                code = homolog.product_variant_id.default_code or ''
                name = homolog.product_variant_id.name
                producto = f"[{code}] {name}"
            else:
                producto = "<span style='color:red;'>No homologado</span>"


            table_html += f"<tr><td>{etiqueta}</td><td>{producto}</td></tr>"

        table_html += "</tbody></table>"

        # Guardamos la tabla directamente en el campo
        archivo.etiquetas_xml_html = table_html

    def _crear_lineas_retencion(self, root, archivo):
        lines = []

        impuestos = root.findall('.//impuestos/impuesto')

        if impuestos:
            for imp in impuestos:
                porcentaje = float(imp.findtext('porcentajeRetener', '0') or 0)

                tax = self.env['account.tax'].search([
                    ('tax_group_id.name', 'in', [
                        'Retención IVA en Compras',
                        'Purchase Profit Withhold',
                    ]),
                    ('amount_type', '=', 'percent'),
                ], limit=0)


                tax = tax.filtered(
                    lambda t: abs(t.amount) == porcentaje
                )[:1]

                numdoc_sustento = imp.findtext('numDocSustento', '')
                base_imponible = float(imp.findtext('baseImponible', '0'))
                porcentaje = float(imp.findtext('porcentajeRetener', '0'))
                valor_retenido = float(imp.findtext('valorRetenido', '0'))

                lines.append(
                    (0, 0, {
                        'tipo_retencion': tax.id,
                        'numdoc_sustento': numdoc_sustento,
                        'base_imponible': base_imponible,
                        'porcentaje_retenido': porcentaje,
                        'valor_retenido': valor_retenido,
                        })
                    )
        else:
            retenciones = root.findall('.//retenciones/retencion')
            doc_sustento = root.find('.//docSustento/numDocSustento')
            for ret in retenciones:
                porcentaje = float(ret.findtext('porcentajeRetener', '0') or 0)

                tax = self.env['account.tax'].search([
                    ('tax_group_id.name', 'in', [
                        'Retención IVA en Compras',
                        'Purchase Profit Withhold',
                    ]),
                    ('amount_type', '=', 'percent'),
                ], limit=0)


                tax = tax.filtered(
                    lambda t: abs(t.amount) == porcentaje
                )[:1]

                base_imponible = float(ret.findtext('baseImponible', '0'))
                porcentaje = float(ret.findtext('porcentajeRetener', '0'))
                valor_retenido = float(ret.findtext('valorRetenido', '0'))

                lines.append(
                    (0, 0, {
                        'tipo_retencion': tax.id,
                        'numdoc_sustento': doc_sustento.text,
                        'base_imponible': base_imponible,
                        'porcentaje_retenido': porcentaje,
                        'valor_retenido': valor_retenido,
                        })
                    )

        if lines:
            archivo.write({
                'withholding_line_ids': [(5, 0, 0)] + lines
            })

