from odoo import models, fields, api
import base64
import requests
import time
from odoo.exceptions import UserError
import xml.etree.ElementTree as ET
import re
from datetime import datetime
import html
from odoo.exceptions import UserError
from requests.exceptions import RequestException
import logging
_logger = logging.getLogger(__name__)

SOAP_NS = "{http://schemas.xmlsoap.org/soap/envelope/}"

class ArchivoModel(models.Model):
    _name = 'archivo.model'
    _rec_name = 'numero_factura'
    _description = 'Modelo para gestionar archivos de texto'

    fecha_subida = fields.Datetime(string='Fecha de Subida', default=fields.Datetime.now)

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )


    etiquetas_xml_html = fields.Html(
        string="Etiquetas / Productos Odoo",
        sanitize=True,
        sanitize_tags=True,
        store=True,         
    )


    clave_acceso = fields.Char(string='Clave de Acceso')

    numero_factura = fields.Char(string='Nombre')

    factura_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura',
        compute='_compute_factura_relacionada',
        store=False,
        readonly=True,
    )

    serie_comprobante = fields.Char(string='Serie del Comprobante')

    fecha_autorizacion = fields.Datetime(string='Fecha de Autorización')

    fecha_emision = fields.Datetime(string='Fecha de Emisión')

    identificacion_receptor = fields.Char(string='RUC/Cedula Receptor')

    identificacion_emisor = fields.Char(string='RUC/Cedula Emisor')

    valor_sin_impuestos = fields.Float(string='Valor Sin Impuestos')

    iva = fields.Float(string='IVA')

    importe_total = fields.Float(string='Importe Total')

    numero_documento_modificado = fields.Char(string='Número de Documento Modificado')
    
    xml_file = fields.Binary(string="Archivo XML")

    xml_filename = fields.Char(string="Nombre del Archivo XML")

    state = fields.Selection(
        [
            ('importado', 'Importado'),
            ('descargado', 'Descargado'),
            ('rechazado', 'Rechazado'),
            ('validado', 'Validado')
        ],
        string='Estado',
        default='importado',  # El estado por defecto es 'importado'
    )   

    estado_factura = fields.Selection(
        related='factura_id.state',
        string='Estado de la Factura',
        store=True,
        readonly=True
    )
    name_emisor = fields.Char(string="Razón Social Emisor")
    type_doc = fields.Char(string="Tipo Comprobante")

    @api.depends('numero_factura')
    def _compute_factura_relacionada(self):
        # Core típico: 005-001-000000155 o 100-002-023155639
        patt = re.compile(r'\d{3}-\d{3}-\d+')

        for record in self:
            txt = (record.numero_factura or '').strip()
            if not txt:
                record.factura_id = False
                continue

            # Detectar prefijo (para priorización)
            up = txt.upper()
            is_ret = up.startswith('RET')
            is_fact = up.startswith('FACT')

            # Extraer núcleo
            m = patt.search(txt)
            core = m.group(0) if m else txt.split()[-1]  # fallback conservador

            # Variantes a probar (en orden de probabilidad)
            candidatos = [core, txt.replace('FACT', '').replace('Ret', '').strip(), txt]

            domain_base = [
                ('company_id', '=', self.env.company.id),
                ('state', '!=', 'cancel'),
            ]

            # Priorizar por tipo si se detecta prefijo
            # Ajusta según tus move_type reales para retenciones en tu DB
            prio_domain = []
            if is_ret:
                prio_domain = [('move_type', 'in', ('out_withholding', 'in_withholding'))]
            elif is_fact:
                prio_domain = [('move_type', 'in', (
                    'out_invoice', 'out_refund', 'in_invoice', 'in_refund'
                ))]

            Move = self.env['account.move']
            found = Move.browse()

            # 1) Búsqueda priorizada por tipo (si aplica)
            if prio_domain:
                for cand in candidatos:
                    dom = domain_base + prio_domain + ['|', ('name', '=', cand), ('ref', '=', cand)]
                    found = Move.search(dom, limit=1, order='id desc')
                    if found:
                        break

            # 2) Si no se halló, búsqueda amplia sin priorización
            if not found:
                for cand in candidatos:
                    dom = domain_base + ['|', ('name', '=', cand), ('ref', '=', cand)]
                    found = Move.search(dom, limit=1, order='id desc')
                    if found:
                        break

            record.factura_id = found or False
            if found and record.state != 'descargado':
                record.state = 'descargado'

    def action_confirm_register(self):
        # Definir el registro con las claves y valores necesarios
        registro = {
            'CLAVE_ACCESO': self.clave_acceso,
            'TIPO_COMPROBANTE': 'Factura' if 'fac' in self.numero_factura[:3].lower() else 'Retención',
            'SERIE_COMPROBANTE': self.serie_comprobante,
            'FECHA_EMISION': self.fecha_emision.strftime("%d/%m/%Y") if self.fecha_emision else None,
            'RUC_EMISOR': self.identificacion_emisor,
            'IDENTIFICACION_RECEPTOR': self.identificacion_receptor,
            'IMPORTE_TOTAL': self.importe_total,
            'IVA': self.iva,
            'VALOR_SIN_IMPUESTOS': self.valor_sin_impuestos
        }

        record = self.env['account.move'].search([
            ('l10n_ec_authorization_number', '=', registro.get('CLAVE_ACCESO', '')),
            ('ref', '=', registro.get('SERIE_COMPROBANTE', '')),
            ('company_id', '=', self.env.company.id),
            ('state', '!=', 'cancel')  
        ])
        if not record:
            # Pasar el registro a la función process_record
            if self.process_record(registro):
                self.write({'state':'descargado'})
            else:
                self.write({'state':'rechazado'})
        else:
            self.write({'state':'rechazado'})
            raise UserError(registro.get('SERIE_COMPROBANTE', '')+' con clave de acceso:\n'+registro.get('CLAVE_ACCESO', '')+'\nya se encuentra registrado.')

    def process_record(self, registro):
        print("process_record")
        clave_acceso = registro.get('CLAVE_ACCESO', '')
        
        return self.process_comprobante(clave_acceso, registro)

    def process_comprobante(self, clave_acceso, registro):
        print("ingresando comprobante")
        max_retries = 5
        backoff_base = 1  # segundos

        last_err_msg = None
        for attempt in range(1, max_retries + 1):
            ok, root, err_msg = self.send_soap_request(clave_acceso)
            if ok and self.is_valid_response(root):
                try:
                    self.save_comprobante(root, clave_acceso, registro)
                    self.write({'numero_documento_modificado': ' '})
                    return True
                except Exception as e:
                    # Falla procesando el XML válido
                    last_err_msg = f"Error guardando comprobante: {e}"
            else:
                last_err_msg = err_msg or "Respuesta inválida del SRI"

            # backoff sólo si quedan intentos
            if attempt < max_retries:
                time.sleep(backoff_base * attempt)

        # Si llegó aquí, falló todo
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.write({
            'state': 'rechazado',
            'numero_documento_modificado': f"XML no recuperado del SRI - {ahora} - {last_err_msg or 'Error desconocido'}",
        })
        return False


    def send_soap_request(self, clave_acceso):
        """
        Devuelve (ok: bool, root: Element|None, err_msg: str|None)
        """
        wsdl_url = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'
        xml_body = self.build_soap_request_body(clave_acceso)
        headers = {'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': ''}

        try:
            # timeout total razonable: (conexión, lectura)
            resp = requests.post(wsdl_url, data=xml_body, headers=headers, timeout=(10, 30))
        except RequestException as e:
            return False, None, f"Falla de conexión con SRI: {e}"

        if resp.status_code != 200:
            # Algunos proxies devuelven HTML/JSON en errores
            snippet = (resp.text or "").strip()
            if len(snippet) > 300:
                snippet = snippet[:300] + "..."
            return False, None, f"HTTP {resp.status_code} desde SRI: {snippet}"

        # Parseo XML con control de errores
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:
            return False, None, f"XML inválido desde SRI: {e}"

        # Detectar SOAP Fault
        fault = root.find(f".//{SOAP_NS}Fault")
        if fault is not None:
            faultstring = fault.findtext("faultstring") or "SOAP Fault sin detalle"
            return False, root, f"SOAP Fault del SRI: {faultstring}"

        # Puede venir respuesta 200 pero sin comprobantes o con estado NO AUTORIZADO
        # Dejamos que is_valid_response lo evalúe; aquí sólo retornamos OK en parseo
        return True, root, None

    def build_soap_request_body(self, clave_acceso):
        return f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:aut="http://ec.gob.sri.ws.autorizacion">
        <soapenv:Header/>
        <soapenv:Body>
            <aut:autorizacionComprobante>
            <claveAccesoComprobante>{clave_acceso}</claveAccesoComprobante>
            </aut:autorizacionComprobante>
        </soapenv:Body>
        </soapenv:Envelope>
        """.strip()

    def is_valid_response(self, root):
        """
        Considera válido si:
        - numeroComprobantes > 0, y
        - al menos una autorización con estado AUTORIZADO (opcional pero útil), o
        - si tu save_comprobante maneja NO AUTORIZADO, puedes aflojar este criterio.
        """
        try:
            # 1) Conteo de comprobantes
            cnt_node = root.find('.//numeroComprobantes')
            if cnt_node is None or int((cnt_node.text or "0").strip() or 0) <= 0:
                return False

            # 2) Estado (si existe)
            # Estructura típica: .../autorizaciones/autorizacion/estado
            estado = root.findtext('.//autorizaciones/autorizacion/estado')
            if estado is None:
                # Si no hay estado, lo dejamos pasar si hay comprobantes
                return True

            estado = (estado or "").strip().upper()
            # Ajusta según tu lógica: si sólo quieres descargar AUTORIZADO:
            return estado in ("AUTORIZADO", "PROCESO")  # PROCESO: a veces aparece
        except Exception:
            return False
    
    def update_products(self):
        """
        Este método toma el XML ya guardado, lo decodifica,
        extrae las etiquetas y rellena la tabla con las homologaciones actuales.
        """
        for rec in self:
            if not rec.xml_file:
                raise UserError("Este registro no contiene un archivo XML guardado.")

            try:
                decoded_text = base64.b64decode(rec.xml_file).decode('utf-8')
                comprobante_root = ET.fromstring(decoded_text)
                etiquetas = [
                    det.find('descripcion').text.strip()
                    for det in comprobante_root.findall('.//detalle')
                    if det.find('descripcion') is not None
                ]

                table_html  = "<table class='table table-sm o_table' style='width:100%;'>"
                table_html += "<thead><tr><th>Etiqueta XML</th><th>Producto Odoo</th></tr></thead><tbody>"

                for etiqueta in etiquetas:
                    homolog = rec.env['product.homologation'].search(
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
                rec.etiquetas_xml_html = table_html

            except Exception as e:
                raise UserError(f"No se pudo procesar el XML guardado:\n{str(e)}")


    def save_comprobante(self, root, clave_acceso, registro):
        print("save_comprobante")
        decoded_text = html.unescape(root.find('.//comprobante').text)
        encoded_xml = base64.b64encode(decoded_text.encode('utf-8'))


        self.write({'xml_file':encoded_xml,'xml_filename':'archivo.xml'})

        try:
            comprobante_root = ET.fromstring(decoded_text)
            etiquetas = [
                det.find('descripcion').text.strip()
                for det in comprobante_root.findall('.//detalle')
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
            print(table_html)

            # Guardamos la tabla directamente en el campo
            self.etiquetas_xml_html = table_html

        except Exception as e:
            print("No se pudieron extraer etiquetas:", e)

    def action_generate_invoice(self):
        """
        Botón disponible SOLO en estado 'descargado'.
        Crea la factura o la retención y avanza el workflow.
        """
        for rec in self:
            if rec.state != 'descargado':
                raise UserError("El documento debe estar en estado DESCARGADO para generar la factura.")

            # reconstruir el XML desde el binario
            xml_text = base64.b64decode(rec.xml_file or b'').decode('utf-8')
            root     = ET.fromstring(xml_text)

            # recrear el diccionario 'registro' usando los campos del propio record
            registro = {
                'CLAVE_ACCESO'         : rec.clave_acceso,
                'TIPO_COMPROBANTE'     : 'Factura' if 'fac' in (rec.numero_factura or '')[:3].lower() else 'Retención',
                'SERIE_COMPROBANTE'    : rec.serie_comprobante,
                'FECHA_EMISION'        : rec.fecha_emision.strftime("%d/%m/%Y") if rec.fecha_emision else None,
                'RUC_EMISOR'           : rec.identificacion_emisor,
                'IDENTIFICACION_RECEPTOR': rec.identificacion_receptor,
                'IMPORTE_TOTAL'        : rec.importe_total,
                'IVA'                  : rec.iva,
                'VALOR_SIN_IMPUESTOS'  : rec.valor_sin_impuestos,
            }

            # ---- dentro de action_generate_invoice() ----
            xml_text = base64.b64decode(rec.xml_file or b'').decode('utf-8')

            # ➜ Creamos un pequeño wrapper que imita la estructura original
            wrapper_root      = ET.Element('root')
            comprobante_node  = ET.SubElement(wrapper_root, 'comprobante')
            comprobante_node.text = xml_text      # CDATA en el flujo original

            # Ahora pasamos wrapper_root (no xml_text) a create_invoice
            receptor = rec.create_or_get_partner(registro)
            rec.create_invoice(wrapper_root, receptor, registro)

            # opcional: pasar directamente a 'validado'
            rec.write({'state': 'validado'})

    def create_or_get_partner(self, registro):
        """
        Devuelve el partner cuyo VAT coincide con el RUC/C.I. del emisor.
        Si no existe, NO lo crea; lanza un UserError indicando que
        el proveedor debe existir previamente.
        """
        identificacion_receptor = registro.get('RUC_EMISOR', '')
        partner = self.env['res.partner'].search(
            [('vat', '=', identificacion_receptor)],
            limit=1
        )

        if not partner:
            raise UserError(
                f"Debe crear previamente el proveedor con RUC/Cédula "
                f"{identificacion_receptor} antes de continuar."
            )
        return partner

    def create_partner(self, identificacion_receptor):

        tipo_identificacion = self.identificar_tipo(identificacion_receptor)
        company_type_value = 'person' if tipo_identificacion == "Cédula" else 'company'
        l10n_ec_type = self.get_identification_type(tipo_identificacion)

        return self.env['res.partner'].create({
            'name': f'Receptor {identificacion_receptor}',
            'vat': identificacion_receptor,
            'company_type': company_type_value,
            'l10n_latam_identification_type_id': l10n_ec_type.id,
            'company_id': self.env.company.id,
            'type': 'contact',
        })

    def get_identification_type(self, tipo_identificacion):
        if tipo_identificacion == "Cédula":
            return self.env['l10n_latam.identification.type'].search([('name', '=', '{"en_US": "Citizenship", "es_EC": "Cédula"}')], limit=1)
        elif tipo_identificacion == "RUC":
            return self.env['l10n_latam.identification.type'].search([('name', '=', '{"en_US": "RUC"}')], limit=1)
        return None

    def create_invoice(self, root, receptor, registro):
        ref_factura = registro.get('SERIE_COMPROBANTE')
        ruc_emisor = registro.get('RUC_EMISOR')

        # Buscar proveedor por RUC
        partner = self.env['res.partner'].search([('vat', '=', ruc_emisor)], limit=1)
        if not partner:
            raise UserError("El proveedor con RUC %s no existe." % ruc_emisor)
        
        domain = [
            ('move_type', '=', 'in_invoice'),
            ('name', '=', self.numero_factura),
            ('partner_id', '=', partner.id),
            ('company_id', '=', self.env.company.id),
            ('state', '!=', 'cancel')
        ]

        _logger.info("Validando duplicado de factura con filtros: %s", domain)

        factura_existente = self.env['account.move'].search(domain, limit=1)

        if factura_existente:
            _logger.warning("Factura duplicada detectada: ID=%s, name=%s", factura_existente.id, factura_existente.name)
            raise UserError("Ya existe una factura registrada con ese número y proveedor.")
        else:
            _logger.info("No se encontró duplicado. Procediendo a crear factura.")
        
        tipo_comprobante = registro.get('TIPO_COMPROBANTE')
        if tipo_comprobante == 'Factura':
            detalles_producto = self.extract_invoice_details(root)
            fecha_formateada = self.format_date(registro.get('FECHA_EMISION'))

            company_tax = self.env['res.company'].browse(self.env.company.id)
            porcentaje_tax = self.extraer_porcentaje(company_tax.account_purchase_tax_id.name)

            if receptor.vat != registro.get('RUC_EMISOR', ''):
                raise UserError(_(
                    "El RUC del proveedor (%s) no coincide con el RUC del emisor en el XML (%s)."
                ) % (receptor.vat, registro.get('RUC_EMISOR', '')))
                
            get_journal = self.env['account.journal'].search([
                ('type', '=', 'purchase'),
                ('company_id', '=', self.env.company.id),
                ('l10n_ec_is_purchase_liquidation', '=', False),
                ('l10n_latam_use_documents', '=', True),
            ], limit=1) or False

            factura = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': receptor.id,
                'invoice_date': fecha_formateada,
                'company_id': self.env.company.id,
                'journal_id': get_journal.id,
                'ref': registro.get('SERIE_COMPROBANTE'),
                'date': fecha_formateada,
                # Se comenta para que no asigne secuencia de factura automatico hasta definir bien el diario
                #'l10n_latam_document_number': registro.get('SERIE_COMPROBANTE'),
                'l10n_latam_document_type_id': self.env['l10n_latam.document.type'].search([
                    ('code', '=', registro.get('CLAVE_ACCESO')[8:10])
                ], limit=1).id,
                'l10n_ec_authorization_number': registro.get('CLAVE_ACCESO'),
                'amount_tax': float(registro.get('IVA', '')),
                'is_authorization_pressed':True,
                'invoice_line_ids': [(0, 0, {
                    'product_id': self.get_product_id_from_description(detalle['description']),
                    'name': detalle['description'],
                    'quantity': detalle['quantity'],
                    'price_unit': detalle['unit_price'],
                    'price_subtotal': detalle['total_price'],
                    'price_total': detalle['total_price'],
                    'tax_ids': [(6, 0, self._get_tax_id(detalle['tax_porcentage'], company_tax, porcentaje_tax))]
                }) for detalle in detalles_producto],
            })

            # → Asignar forma de pago automáticamente
            forma_pago = self.env['account.move']._extract_forma_pago(self)
            _logger.info("Forma de pago extraída: %s", forma_pago)
            if forma_pago:
                sri_payment = self.env['l10n_ec.sri.payment'].search([('code', '=', forma_pago)], limit=1)
                if sri_payment:
                    factura.l10n_ec_sri_payment_id = sri_payment
                else:
                    _logger.warning("No se encontró código de forma de pago en sri.payment: %s", forma_pago)

            return factura

        else:
            _logger.info("Entrando a lógica de retención")
            
            #Retencion
            num_doc_sustento = None

            detalles_retencion = self.extract_retention_details(root)
            _logger.info("Detalles retención: %s", detalles_retencion)

            if detalles_retencion:
                comprobante_node = root.find('.//comprobante')
                if comprobante_node is not None and comprobante_node.text:
                    try:
                        comprobante_root = ET.fromstring(comprobante_node.text)
                        num_doc_sustento = comprobante_root.findtext('.//docsSustento/docSustento/numDocSustento')
                        _logger.info("numDocSustento encontrado en nodo <comprobante>: %s", num_doc_sustento)
                    except Exception as e:
                        _logger.warning("Error al procesar nodo <comprobante>: %s", e)
            else:
                _logger.info("Intentando estructura alternativa con XML embebido dentro de <comprobante>...")
                comprobante_node = root.find('.//comprobante')
                if comprobante_node is not None and comprobante_node.text:
                    try:
                        comprobante_root = ET.fromstring(comprobante_node.text)
                        detalles_retencion = self.extract_retention_details_alt(comprobante_root)
                        _logger.info("Detalles alternativos de retención: %s", detalles_retencion)

                        impuestos_list = comprobante_root.findall('.//impuestos/impuesto')
                        _logger.info("Cantidad de nodos <impuesto> encontrados: %s", len(impuestos_list))
                        for impuesto_xml in impuestos_list:
                            num_doc_sustento = impuesto_xml.findtext('numDocSustento')
                            _logger.info("Leyendo numDocSustento desde nodo <impuesto>: %s", num_doc_sustento)
                            if num_doc_sustento:
                                break
                    except Exception as e:
                        _logger.warning("Error al parsear XML interno en <comprobante>: %s", e)
                else:
                    _logger.warning("No se encontró el nodo <comprobante> o está vacío.")

            if not num_doc_sustento:
                raise UserError("No se encontró el número de documento de sustento en el XML.")

            # Formatear número de documento
            try:
                parte1 = num_doc_sustento[:3]
                parte2 = num_doc_sustento[3:6]
                parte3 = num_doc_sustento[6:]
                num_doc_sustento_formateado = f"Ret {parte1}-{parte2}-{parte3}"
            except Exception as e:
                _logger.warning("Error al formatear numDocSustento '%s': %s", num_doc_sustento, e)
                num_doc_sustento_formateado = num_doc_sustento

            fecha_formateada = self.format_date(registro.get('FECHA_EMISION'))

            # Buscar la configuración de diario para retenciones
            config = self.env['advance.config.docs'].search([], limit=1)
            if not config or not config.advance_docs_journal_id:
                raise UserError("No se ha configurado un Diario de Retenciones en 'Configuración de Diario de Retenciones'.")

            journal = config.advance_docs_journal_id

            if not journal:
                raise UserError("No existe un Diario configurado para Retenciones")

            account_move = self.env['account.move'].search([
                ('company_id', '=', self.env.company.id),
                ('name', '=', num_doc_sustento_formateado),
            ])

            if not account_move:
                #raise UserError('La factura de sustento ' + num_doc_sustento_formateado + ' no se encuentra en el sistema.')
                # Crear docuemnto automáticamente si no se encuentra
                account_move = self.env['account.move'].create({
                    'partner_id': account_move.partner_id.id,
                    'journal_id': journal.id,
                    'date': fecha_formateada,
                    'invoice_date': fecha_formateada,
                    'l10n_ec_withhold_date': fecha_formateada,
                    'invoice_origin': num_doc_sustento_formateado,
                    'ref': registro.get('SERIE_COMPROBANTE'),
                    'currency_id': self.env.company.currency_id.id,
                    'l10n_latam_use_documents': True,
                    'l10n_latam_document_type_id': self.env['l10n_latam.document.type'].search([('code', '=', '07')], limit=1).id,
                })

                # Crear líneas de retención
                lines = []

                for detalle in detalles_retencion:
                    impuesto_id = detalle['tipo_retencion']
                    cuenta_id = detalle['cuenta']
                    base_imponible = detalle['base_imponible']

                    impuesto = self.env['account.tax'].browse(impuesto_id)

                    if not cuenta_id:
                        raise UserError("El impuesto '%s' no tiene cuenta contable configurada." % impuesto.name)

                    lines.append((0, 0, {
                        'move_id': account_move.id,
                        'name': f"Retención {impuesto.name}",
                        'account_id': cuenta_id,
                        'credit': base_imponible,
                        'debit': 0.0,
                        'tax_ids': [(6, 0, [impuesto_id])],
                    }))

                account_move.write({'l10n_ec_withhold_line_ids': lines})

                # Ajustar líneas automáticas
                for line in account_move.l10n_ec_withhold_line_ids:
                    account_move.line_ids.create({
                        'move_id': account_move.id,
                        'name': line.name,
                        'account_id': line.account_id.id,
                        'debit': line.credit,
                        'credit': 0.0
                    })

                #for line in account_move.line_ids:
                #    if line.name == "Balance automático de línea":
                #        nuevo_account_id = journal.account_withhold.id
                #        line.write({'account_id': nuevo_account_id})
            else:
                # Validar que la fecha de la factura coincida con la fecha de la retención
                if account_move.date != fecha_formateada:
                    raise UserError(
                        "La fecha contable de la factura (%s) no coincide con la fecha de emisión de la retención (%s)." %
                        (account_move.date.strftime('%Y-%m-%d'), fecha_formateada)
                    )
                
                # Validar que la base imponible de la retención coincida con la de la factura
                base_retencion_total = sum([float(det['base_imponible']) for det in detalles_retencion])
                base_factura = account_move.amount_untaxed

                if round(base_retencion_total, 2) != round(base_factura, 2):
                    raise UserError(
                        "La base imponible de la retención (%.2f) no coincide con el valor imponible de la factura (%.2f)." %
                        (base_retencion_total, base_factura)
                    )
                
                # Validar que no exista otra retención activa para esta factura
                retenciones_existentes = self.env['account.move'].search([
                    ('move_type', '=', 'entry'),
                    ('l10n_ec_related_withhold_line_ids.l10n_ec_withhold_invoice_id', '=', account_move.id),
                    ('state', '!=', 'cancel'),
                    ('company_id', '=', self.env.company.id)
                ])

                if retenciones_existentes:
                    ret = retenciones_existentes[0]
                    raise UserError(_(
                        "Ya existe una retención activa asociada a esta factura:\n"
                        "- Número: %s\n"
                        "Solo puede registrar una nueva si la anterior está anulada."
                    ) % (ret.name))

                # Si no hay retención existente → crear nueva
                
                account = self.env['account.move'].create({
                    'move_type': 'entry',
                    'partner_id': account_move.partner_id.id,
                    'invoice_date': fecha_formateada,
                    'company_id': self.env.company.id,
                    'ref': registro.get('SERIE_COMPROBANTE'),
                    'l10n_ec_withhold_date': fecha_formateada,
                    'journal_id': journal.id,
                    'l10n_latam_document_number': registro.get('SERIE_COMPROBANTE'),
                    'l10n_latam_document_type_id': self.env['l10n_latam.document.type'].search([
                        ('code', '=', '07')
                    ], limit=1).id,
                    'l10n_ec_authorization_number': registro.get('CLAVE_ACCESO'),
                    'amount_total': sum([float(detalle['valor_retenido']) for detalle in detalles_retencion]),
                    'amount_tax': 0.0,
                    'amount_untaxed': 0.0,
                })

                account.write({'l10n_ec_related_withhold_line_ids': [(0, 0, {
                    'move_id': account.id,
                    'account_id': detalle['cuenta'],
                    'balance': float(detalle['base_imponible']),
                    'price_unit': float(detalle['base_imponible']),
                    'price_subtotal': 0,
                    'l10n_ec_withhold_invoice_id': account_move.id,
                    'tax_ids': [detalle['tipo_retencion']]
                }) for detalle in detalles_retencion]})

                for line in account.l10n_ec_related_withhold_line_ids:
                    if line.l10n_ec_withhold_invoice_id:
                        line.write({'l10n_ec_withhold_invoice_id': account_move.id})

                return account


                    
    def extract_invoice_details(self, root):
        detalles_producto = []
        comprobante_root = ET.fromstring(root.find('.//comprobante').text)

        for detalle in comprobante_root.findall('.//detalle'):
            descripcion = detalle.find('descripcion').text
            cantidad = float(detalle.find('cantidad').text)
            precio_unitario = float(detalle.find('precioUnitario').text)
            precio_total_sin_impuesto = float(detalle.find('precioTotalSinImpuesto').text)
            tarifa = float(detalle.find('.//impuesto/tarifa').text)
            valor = float(detalle.find('.//impuesto/valor').text)

            detalles_producto.append({
                'description': descripcion,
                'quantity': cantidad,
                'unit_price': precio_unitario,
                'total_price': precio_total_sin_impuesto,
                'tax_porcentage': tarifa,
                'tax_value': valor
            })
        return detalles_producto

    def format_date(self, fecha):
        return datetime.strptime(fecha, "%d/%m/%Y").strftime("%Y-%m-%d")

    def identificar_tipo(self, numero_identificacion):
        return "Cédula" if re.match(r'^\d{10}$', numero_identificacion) else "RUC" if re.match(r'^\d{13}$', numero_identificacion) else "Pasaporte"

    def extraer_porcentaje(self, texto_impuesto):
        porcentaje_str = re.search(r'(\d{1,2})%', texto_impuesto)
        return int(porcentaje_str.group(1)) if porcentaje_str else 12

    def _get_tax_id(self, tax_percentage, company_tax, porcentaje_tax):
        if company_tax.account_purchase_tax_id.amount == tax_percentage:
            tax_id = company_tax.account_purchase_tax_id
        else:
            # Reemplazar el porcentaje en el nombre del impuesto
            text = company_tax.account_purchase_tax_id.name.replace(
                str(company_tax.account_purchase_tax_id.amount), str(porcentaje_tax))
            tax_id = self.env['account.tax'].search([('name', '=', text)], limit=1)
        return [int(tax_id.id)]
    
    def get_product_id_from_description(self, descripcion_producto):
        # 1. Buscar en homologaciones
        descripcion = descripcion_producto.strip()
        homolog = self.env['product.homologation'].search(
            [('etiqueta', '=', descripcion)],
            limit=1
        )
        if homolog and homolog.product_variant_id:
            return homolog.product_variant_id.id

        # 2. Buscar directamente en productos
        producto = self.env['product.product'].search(
            [('name', '=', descripcion)],
            limit=1
        )
        if producto:
            return producto.id

        # 3. No se encontró
        return None

    def extract_retention_details(self, root):
        detalles_retencion = []
        # Encuentra el nodo del comprobante en formato CDATA y lo convierte a XML
        comprobante_root = ET.fromstring(root.find('.//comprobante').text)
        
        # Itera sobre las retenciones dentro del comprobante, no sobre los impuestos
        for retencion in comprobante_root.findall('.//retencion'):
            tipo_retencion = retencion.find('codigo').text
            base_imponible = float(retencion.find('baseImponible').text)
            porcentaje_retenido = float(retencion.find('porcentajeRetener').text)
            valor_retenido = float(retencion.find('valorRetenido').text)
            if tipo_retencion == '1':  # RENTA
                # Buscar impuestos cuyo nombre contenga 'fuente' y que pertenezcan a la compañía actual
                account_id = self.env['account.account'].search([
                    ('name', 'ilike', 'Retenciones en la fuente pagadas'),
                    ('company_ids', 'in', [self.env.company.id])
                ], limit=1)
                impuestos = self.env['account.tax'].search([
                    ('name', 'ilike', 'fuente'),
                    ('company_id', '=', self.env.company.id),
                    ('description', 'ilike', 'retencion'),
                ])
                if porcentaje_retenido.is_integer():
                    porcentaje_retenido_entero = int(porcentaje_retenido)
                else:
                    porcentaje_retenido_entero = porcentaje_retenido

                for impuesto in impuestos:
                    if str(porcentaje_retenido_entero) in impuesto.description:
                        impuesto_id = impuesto
                        break
            elif tipo_retencion == '2':  # IVA
                # Buscar impuestos cuyo nombre contenga 'IVA' y que pertenezcan a la compañía actual
                account_id = self.env['account.account'].search([
                    ('name', 'ilike', 'IVA pagado en retenciones de la fuente'),
                    ('company_ids', 'in', [self.env.company.id])
                ], limit=1)
                impuestos = self.env['account.tax'].search([
                    ('name', 'ilike', 'IVA'),
                    ('company_id', '=', self.env.company.id),
                    ('description', 'ilike', 'retencion'),
                ])
                porcentaje_retenido_entero = int(round(porcentaje_retenido))
                for impuesto in impuestos:
                    if str(porcentaje_retenido_entero) in impuesto.description:
                        impuesto_id = impuesto
                        break
            # Agrega los detalles de la retención a la lista
            primera_cuenta_valida = None
            for line in impuesto_id.invoice_repartition_line_ids:
                if line.account_id.id:
                    primera_cuenta_valida = line.account_id.id
                    break
            detalles_retencion.append({
                'tipo_retencion': impuesto_id.id,
                'cuenta': primera_cuenta_valida,
                'base_imponible': base_imponible,
                'porcentaje_retenido': porcentaje_retenido,
                'valor_retenido': valor_retenido,
            })
        
        return detalles_retencion
    
    def extract_retention_details_alt(self, root):
        detalles_retencion = []

        impuestos_xml = root.findall('.//impuestos/impuesto')

        for impuesto_xml in impuestos_xml:
            tipo_retencion = impuesto_xml.findtext('codigo')
            base_imponible = float(impuesto_xml.findtext('baseImponible', '0'))
            porcentaje_retenido = float(impuesto_xml.findtext('porcentajeRetener', '0'))
            valor_retenido = float(impuesto_xml.findtext('valorRetenido', '0'))

            impuesto_id = None

            if tipo_retencion == '1':  # RENTA
                impuestos = self.env['account.tax'].search([
                    ('name', 'ilike', 'fuente'),
                    ('company_id', '=', self.env.company.id),
                    ('description', 'ilike', 'retencion'),
                ])
            elif tipo_retencion == '2':  # IVA
                impuestos = self.env['account.tax'].search([
                    ('name', 'ilike', 'IVA'),
                    ('company_id', '=', self.env.company.id),
                    ('description', 'ilike', 'retencion'),
                ])
            else:
                continue  # Tipo de retención no reconocido

            porcentaje_entero = int(round(porcentaje_retenido))

            for impuesto in impuestos:
                if str(porcentaje_entero) in (impuesto.description or ''):
                    impuesto_id = impuesto
                    break

            if not impuesto_id:
                continue  # Si no se encuentra un impuesto válido, omitir

            # Buscar la primera cuenta contable válida
            cuenta_contable = None
            for line in impuesto_id.invoice_repartition_line_ids:
                if line.account_id:
                    cuenta_contable = line.account_id.id
                    break

            if not cuenta_contable:
                continue  # Si no se encuentra cuenta contable válida, omitir

            detalles_retencion.append({
                'tipo_retencion': impuesto_id.id,
                'cuenta': cuenta_contable,
                'base_imponible': base_imponible,
                'porcentaje_retenido': porcentaje_retenido,
                'valor_retenido': valor_retenido,
            })

        return detalles_retencion

    def procesar_archivos(self):
        if not self:
            raise UserError("No hay registros seleccionados.")

        # Validar que todos los estados sean iguales
        estados = set(self.mapped('state'))
        if len(estados) > 1:
            raise UserError("Todos los documentos seleccionados deben tener el mismo estado para continuar.")

        estado_actual = estados.pop()  # extraer el único estado

        for record in self:
            if estado_actual == 'importado':
                record.action_confirm_register()
            elif estado_actual == 'descargado':
                record.action_generate_invoice()
            else:
                raise UserError(f"El estado '{estado_actual}' no tiene procesos siguientes.")
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Proceso completado",
                "message": "Todos los archivos fueron procesados correctamente.",
                "type": "success",  
                "sticky": False,  
                "next": {
                    "type": "ir.actions.client",
                    "tag": "reload",
                },
            },
        }