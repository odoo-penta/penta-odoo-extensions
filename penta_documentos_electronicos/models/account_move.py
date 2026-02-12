import base64
from odoo import fields,models, api, _
import logging
from lxml import etree
from odoo.tools.float_utils import float_is_zero
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
class AccountMove(models.Model):
    _inherit = 'account.move'

    is_authorization_pressed = fields.Boolean(string='Authorization Button Pressed', default=False)

    def _check_total_vs_archivo_model(self):
        for factura in self:
            if factura.move_type != 'in_invoice' or not factura.name or not factura.partner_id.vat:
                _logger.info("Factura no válida para validación (move_type, name o RUC faltante): ID=%s", factura.id)
                continue

            domain = [
                ('numero_factura', '=', factura.name),
                ('identificacion_emisor', '=', factura.partner_id.vat),
                ('company_id', '=', factura.company_id.id)
            ]

            _logger.info("Buscando archivo.model con dominio: %s", domain)

            archivo = self.env['archivo.model'].search(domain, limit=1)

            if archivo:
                _logger.info("Archivo encontrado: ID=%s, importe_total=%s, factura.amount_total=%s",
                             archivo.id, archivo.importe_total, factura.amount_total)

                if not float_is_zero(factura.amount_total - archivo.importe_total, precision_rounding=0.01):
                    _logger.warning("Diferencia de montos detectada entre factura y archivo XML")
                    raise UserError(_(
                        "El total de la factura ingresada (%s) no coincide con el valor importado del XML (%s)."
                    ) % (factura.amount_total, archivo.importe_total))
            else:
                _logger.info("No se encontró archivo.model para esta factura.")

    def action_post(self):
        
        for recor in self:
            if recor.is_authorization_pressed:
                recor._check_total_vs_archivo_model()
                recor._check_authorization_and_forma_pago()
        return super().action_post()

    def _check_duplicate_invoice(self, vals):
        if vals.get('move_type') != 'in_invoice':
            return

        partner_id = vals.get('partner_id')
        ref = vals.get('ref')

        if not (partner_id and ref):
            return

        existing = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('partner_id', '=', partner_id),
            ('ref', '=', ref),
            ('company_id', '=', self.env.company.id),
            ('state', '!=', 'cancel')
        ], limit=1)

        if existing:
            raise UserError(_("Ya existe una factura con el mismo número y proveedor."))
    

    def _check_authorization_and_forma_pago(self):
        for move in self:
            if move.move_type != 'in_invoice':
                continue

            domain = [
                ('numero_factura', '=', move.name),
                ('identificacion_emisor', '=', move.partner_id.vat),
                ('company_id', '=', move.company_id.id)
            ]

            _logger.info("Validando autorización y forma de pago con dominio: %s", domain)
            archivo = self.env['archivo.model'].search(domain, limit=1)

            if not archivo:
                raise UserError(_("No existe una factura con ese número y proveedor."))

            if archivo.state not in ('descargado', 'validado'):
                raise UserError(_(
                    "La factura '%s' debe estar en estado 'descargado' o 'validado' en el módulo de documentos electrónicos."
                ) % move.name)

            if archivo.clave_acceso:
                move.l10n_ec_authorization_number = archivo.clave_acceso
                move.invoice_date = archivo.fecha_emision

            forma_pago = self._extract_forma_pago(archivo)
            self.is_authorization_pressed = True
            if forma_pago:
                sri_payment = self.env['l10n_ec.sri.payment'].search([
                    ('code', '=', forma_pago)
                ], limit=1)

                if sri_payment:
                    move.l10n_ec_sri_payment_id = sri_payment
                else:
                    _logger.warning("Forma de pago no encontrada: %s", forma_pago)

    def action_extract_authorization_number(self):
        try:
            self._check_authorization_and_forma_pago()
        except UserError as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error de Validación",
                    "message": str(e),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return True
    
    def _extract_forma_pago(self, archivo):
        """Extrae el valor de <formaPago> desde el campo xml_file."""
        try:
            if not archivo.xml_file:
                return None

            xml_data = base64.b64decode(archivo.xml_file)
            root = etree.fromstring(xml_data)

            forma_pago = root.find('.//pago/formaPago')
            return forma_pago.text if forma_pago is not None else None

        except Exception as e:
            _logger.error(f"[ERROR] No se pudo procesar el XML: {str(e)}")
            return None