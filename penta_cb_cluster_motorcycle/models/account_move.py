from odoo import api, fields, models
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
        el = etree.SubElement(parent, tag **{k: str(v) for k, v in attrs.items() if v is not None})
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
    
    def _build_invoice_xml(self):
        """
        Return tree XML (etree.Element) for the invoice.
        This method can be overridden to customize the XML structure.
        """
        self.ensure_one()
        if self.move_type not in ("our_invoice", "in_invoice"):
            raise UserError(_("Only support customer/vendor invoices."))
        
        root = etree.SubElement("ventas")
        
        # -------- datosRegistrador --------
        datosRegistrador = etree.SubElement(root, "datosRegistrador")
        self._xml_element(datosRegistrador, "numeroRUC", self.name or "")
        
        # -------- datosVentas --------
        datosVentas = etree.SubElement(root, "datosVentas")
        # -------- venta (multiple) -------
        venta = etree.SubElement(datosVentas, "venta")
        self._xml_element(venta, "rucComercializador", self.partner_id.vat or "")
        self._xml_element(venta, "CAMVCpn", self.name or "")
        
        
        
    def get_xml_invoice(self):
        self.ensure_one()
        return self.cb_xml_invoice_id
    