from odoo import api, fields, models, _
from odoo.exceptions import UserError
from lxml import etree as LET
from datetime import datetime
import base64
import unicodedata
import re
from odoo.tools import xml_element, sanitize_text, split_doc_number, latam_id_code, doc_type_code

# ---------- Region por provincia ----------
COSTA = {"el oro", "esmeraldas", "guayas", "los rios", "manabi", "santa elena", "santo domingo de los tsachilas", "santo domingo"}
SIERRA = {"azuay", "bolivar", "cañar", "carchi", "cotopaxi", "chimborazo", "imbabura", "loja", "pichincha", "tungurahua"}
ORIENTE = {"morona santiago", "napo", "pastaza", "zamora chinchipe", "sucumbios", "orellana"}
GALAPAGOS = {"galapagos"}

def ec_region_prefix(state):
    """Devuelve '1','2','3','4' según la región de la provincia (por nombre)."""
    if not state:
        return ""
    n = (state.name or "").strip().lower()
    if n in COSTA:
        return "1"
    if n in SIERRA:
        return "2"
    if n in ORIENTE:
        return "3"
    if n in GALAPAGOS:
        return "4"
    # Fallback por si el nombre trae adornos (ej. 'Sto. Domingo...')
    base = re.sub(r"[^a-z ]", "", n)
    if base in COSTA:
        return "1"
    if base in SIERRA:
        return "2"
    if base in ORIENTE:
        return "3"
    if base in GALAPAGOS:
        return "4"
    return ""  # si no reconoce, mejor en blanco para que se note la falta

class AccountMove(models.Model):
    _inherit = 'account.move'

    # ----------------- Helpers de fecha y líneas -----------------
    def _format_date(self, date):
        if not date:
            return ""
        if isinstance(date, str):
            return date
        if isinstance(date, datetime):
            return date.date().isoformat()
        return date.isoformat()

    def _iter_invoice_lines(self):
        return self.invoice_line_ids.filtered(lambda l: not l.display_type)

    # ----------------- Resolución de código de cantón -----------------
    def _compute_canton_code_from_partner(self, partner):
        """
        Construye: <region><state.code><city_code(2d)>
        city_code:
            - si partner.city_id existe: usa city_id.l10n_ec_code o city_id.code
            - si no existe city_id y existe modelo 'res.country.state.city':
                busca por (name == partner.city) & (state_id == partner.state_id)
        """
        state = partner.state_id
        if not state:
            return ""

        region = ec_region_prefix(state)
        state_code = (state.code or "").strip()

        # 1) intenta via city_id m2o si existe
        city_code = ""
        if hasattr(partner, "city_id") and partner.city_id:
            city = partner.city_id
            city_code = (getattr(city, "l10n_ec_code", None) or getattr(city, "code", None) or "")  # trescloud o modelo pentalab_parish
        # 2) fallback via texto + modelo alterno (pentalab_parish)
        if (not city_code) and partner.city and ("res.country.state.city" in self.env):
            Alt = self.env["res.country.state.city"]
            alt = Alt.search([
                ("name", "=", partner.city),
                ("state_id", "=", state.id),
            ], limit=1)
            if alt:
                city_code = (getattr(alt, "l10n_ec_code", None) or getattr(alt, "code", None) or "")

        city_code = str(city_code).strip()
        if city_code and len(city_code) == 1:
            city_code = "0" + city_code  # rellena a 2 dígitos
        # Si city_code viene >2 (raro), no lo recortes; es mejor que se note para depurar.

        return f"{region}{state_code}{city_code}" if (region and state_code and city_code) else ""

    # ----------------- Constructor de XML -----------------
    def _build_invoice_xml_tree(self):

        def build_direccion(parent, partner):
            datos_direccion = LET.SubElement(parent, "datosDireccion")
            xml_element(datos_direccion, "tipo", "RESIDENCIA")
            # usa street_name/number si existen; si no, street/street2
            calle = getattr(partner, "street_name", None) or partner.street or ""
            numero = getattr(partner, "street_number", None) or ""
            inter = getattr(partner, "street2", None) or ""
            xml_element(datos_direccion, "calle", calle)
            xml_element(datos_direccion, "numero", numero)
            xml_element(datos_direccion, "interseccion", inter)

        def build_telefono(parent, partner):
            datos_telefono = LET.SubElement(parent, "datosTelefono")
            prov = getattr(getattr(partner, "state_id", False), "l10n_ec_penta_code_state", "") or ""
            xml_element(datos_telefono, "provincia", prov)
            xml_element(datos_telefono, "numero", partner.phone or "")

        def build_venta(parent, company, partner, latam_doc_type, latam_doc_number,
                        auth_number, invoice_date, price, lot=None):
            venta = LET.SubElement(parent, "venta")
            xml_element(venta, "rucComercializador", company.vat or "")
            xml_element(venta, "CAMVCpn", getattr(lot, "ramv", "") if lot else "")
            xml_element(venta, "serialVin", getattr(lot, "name", "") if lot else "")
            xml_element(venta, "nombrePropietario", partner.name or "")
            xml_element(venta, "tipoIdentificacionPropietario", latam_id_code(partner))
            xml_element(venta, "tipoComprobante", doc_type_code(latam_doc_type))

            est, pto, num = split_doc_number(latam_doc_number)
            xml_element(venta, "establecimientoComprobante", est)
            xml_element(venta, "puntoEmisionComprobante", pto)
            xml_element(venta, "numeroComprobante", num)

            xml_element(venta, "numeroAutorizacion", auth_number or "")
            xml_element(venta, "fechaVenta", self._format_date(invoice_date) or "")
            xml_element(venta, "precioVenta", "%.2f" % (price if price is not None else 0.0))

            # === AQUÍ calculamos el codigoCantonMatriculacion desde account.move ===
            canton = self._compute_canton_code_from_partner(partner)
            xml_element(venta, "codigoCantonMatriculacion", canton)

            build_direccion(venta, partner)
            build_telefono(venta, partner)

        def build_registrador_section(root, invoice):
            datos_registrador = LET.SubElement(root, "datosRegistrador")
            xml_element(datos_registrador, "numeroRUC", invoice.company_id.vat or "")

        def build_ventas_section(root):
            return LET.SubElement(root, "datosVentas")

        def process_invoice(inv, datos_ventas):
            lots = getattr(inv, "stock_lot_ids", [])  # ajusta al nombre real de tu campo
            if lots:
                for lot in lots:
                    build_venta(
                        datos_ventas,
                        inv.company_id,           # company
                        inv.partner_id,           # partner
                        inv.l10n_latam_document_type_id,
                        inv.l10n_latam_document_number,
                        getattr(inv, "l10n_ec_authorization_number", "") or "",
                        inv.invoice_date,
                        inv.amount_total,
                        lot
                    )
            else:
                build_venta(
                    datos_ventas,
                    inv.company_id,
                    inv.partner_id,
                    inv.l10n_latam_document_type_id,
                    inv.l10n_latam_document_number,
                    getattr(inv, "l10n_ec_authorization_number", "") or "",
                    inv.invoice_date,
                    inv.amount_total,
                    None
                )

        if not self:
            return None

        bad = self.filtered(lambda m: m.move_type not in ("out_invoice", "in_invoice"))
        if bad:
            raise UserError(_("Only support customer/vendor invoices."))

        root = LET.Element("ventas")
        build_registrador_section(root, self[0])
        datos_ventas = build_ventas_section(root)

        for inv in self:
            process_invoice(inv, datos_ventas)

        return root

    def generate_invoice_xml(self):
        root = self._build_invoice_xml_tree()
        return LET.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)

    def get_xml_invoice(self):
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
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

        
        