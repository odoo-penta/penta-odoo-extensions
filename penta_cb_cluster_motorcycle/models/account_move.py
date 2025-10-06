
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from lxml import etree
import base64
from datetime import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'

    cb_xml_invoice_id = fields.Many2one(
        comodel_name='cb.xml.invoice',
        string='CB XML Invoice',
        ondelete='set null',
        index=True,
        copy=False,
    )

    @api.model
    def create(self, vals):
        move = super().create(vals)
        if move.cb_xml_invoice_id:
            move.cb_xml_invoice_id.state = 'posted'
        return move
    
    def _xml_element(self, parent , tag, text=None, **attrs):
        """Helper to create an XML element with optional text and attributes."""
        el = etree.SubElement(parent, tag, **{k: str(v) for k, v in attrs.items() if v is not None})
        if text is not None:
            el.text = str(text)
        return el
    
    def _format_date(self, date):
        """Format date as ISO simple string (YYYY-MM-DD)."""
        if not date:
            return ""
        # date can be fields.Date (str) or datetime/Dare
        if isinstance(date, str):
            return date
        if isinstance(date, datetime):
            return date.date().isoformat()
        return date.isoformat()
    
    def _iter_invoice_lines(self):
        """'Real' lines (discard secction/notes)."""
        return self.invoice_line_ids.filtered(lambda l: not l.display_type)
    
    # -------------------------------------- Core methods: Build tree XML --------------------------------------
    
    def _build_invoice_xml_tree(self, is_multiple=False):
        """
        Return tree XML (etree.Element) for the invoice.
        This method can be overridden to customize the XML structure.
        """

        def build_direccion(parent, partner):
            datos_direccion = etree.SubElement(parent, "datosDireccion")
            self._xml_element(datos_direccion, "tipo", "RESIDENCIA")
            self._xml_element(datos_direccion, "calle", partner.street_name or "")
            self._xml_element(datos_direccion, "numero", getattr(partner, "street_number", "") or "")
            self._xml_element(datos_direccion, "interseccion", getattr(partner, "street2", "") or "")

        def build_telefono(parent, partner):
            datos_telefono = etree.SubElement(parent, "datosTelefono")
            self._xml_element(datos_telefono, "provincia", getattr(partner.state_id, "l10n_ec_penta_code_state", "") or "")
            self._xml_element(datos_telefono, "numero", partner.phone or "")

        def build_venta(parent, company, partner, l10n_latam_document_type_id, l10n_latam_document_number, l10n_ec_authorization_number, invoice_date, price, lot=None):
            venta = etree.SubElement(parent, "venta")
            self._xml_element(venta, "rucComercializador", company.vat or "")
            self._xml_element(venta, "CAMVCpn", getattr(lot, "ramv", "") if lot else "")
            self._xml_element(venta, "serialVin", getattr(lot, "name", "") if lot else "")
            self._xml_element(venta, "nombrePropietario", partner.name or "")
            tipo_identificacion = ""
            if partner.l10n_latam_identification_type_id == 5:
                tipo_identificacion = "C"
            elif partner.l10n_latam_identification_type_id == 6:
                tipo_identificacion = "P"
            elif partner.l10n_latam_identification_type_id == 4:
                tipo_identificacion = "R"
            self._xml_element(venta, "tipoIdentificacionPropietario", tipo_identificacion)
            self._xml_element(venta, "tipoComprobante", getattr(l10n_latam_document_type_id, "l10n_ec_penta_code_state", "") or "")
            self._xml_element(venta, "establecimientoComprobante", l10n_latam_document_number[:3] if l10n_latam_document_number else "")
            self._xml_element(venta, "puntoEmisionComprobante", l10n_latam_document_number[4:6] if l10n_latam_document_number else "")
            self._xml_element(venta, "numeroComprobante", l10n_latam_document_number[7:] if l10n_latam_document_number else "")
            self._xml_element(venta, "numeroAutorizacion", l10n_ec_authorization_number or "")
            self._xml_element(venta, "fechaVenta", self._format_date(invoice_date) or "")
            self._xml_element(venta, "precioVenta", "%.2f" % price if price is not None else "0.00")
            self._xml_element(venta, "codigoCantonMatriculacion",  partner.city_id.l10n_ec_penta_code_city if partner.city_id else "")
            build_direccion(venta, partner)
            build_telefono(venta, partner)

        def build_registrador_section(root, invoice):
            datos_registrador = etree.SubElement(root, "datosRegistrador")
            self._xml_element(datos_registrador, "numeroRUC", invoice.company_id.vat or "")

        def build_ventas_section(root):
            return etree.SubElement(root, "datosVentas")

        def process_invoice(invoice, datos_ventas):
            for lot in invoice.stock_lot_ids:
                build_venta(
                    datos_ventas,
                    invoice.partner_id,
                    invoice.company_id,
                    invoice.l10n_latam_document_type_id,
                    invoice.l10n_latam_document_number,
                    invoice.l10n_ec_authorization_number,
                    invoice.invoice_date,
                    invoice.amount_total,
                    lot
                )

        if not self:
            return None

        invoice = self[0]
        if invoice.move_type not in ("out_invoice", "in_invoice"):
            raise UserError(_("Only support customer/vendor invoices."))

        root = etree.Element("ventas")
        build_registrador_section(root, invoice)
        datos_ventas = build_ventas_section(root)
        for invoices in self:
            process_invoice(invoices, datos_ventas)

        return root
    
    def generate_invoice_xml(self):
        """
        Return the bites of the XML file for the invoice.
        """
        root = self._build_invoice_xml_tree()
        xml_bytes = etree.tostring(
            root,
            xml_declaration=True,
            encoding="UTF-8",
            pretty_print=True
        )
        return xml_bytes

    # ------------- Guardar como adjunto y descargar -------------
    def get_xml_invoice(self):
        """
        Crea un adjunto con el XML y devuelve una acción de descarga.
        Útil para ponerlo en un botón del formulario.
        """
        
        xml_bytes = self.generate_invoice_xml()
        
        ts = fields.Datetime.now().strftime("%Y%m%d-%H%M%S")
        fname = f"ventas_{len(self)}fact_{ts}.xml"

        attachment = self.env["ir.attachment"].create({
            "name": fname,
            "res_model": self[0]._name,
            "res_id": self[0].id,
            "type": "binary",
            "datas": base64.b64encode(xml_bytes),
            "mimetype": "application/xml",
        })

        # Act URL: descarga directa
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
        
        
        