from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ExtendedRemission(models.Model):
    _inherit = 'stock.picking'

    driver_name = fields.Char(string='Nombre del Conductor', store=True)
    driver_id = fields.Char(string='Cédula del Conductor', store=True)

    invoice_number = fields.Char(string='Número de Factura', compute='_compute_invoice_number', store=False)

    @api.depends('origin')
    def _compute_invoice_number(self):
        for picking in self:
            invoice_num = ''
            if picking.origin:
                invoices = self.env['account.move'].search([
                    ('invoice_origin', '=', picking.origin),
                    ('state', '=', 'posted'),
                ])
                if invoices:
                    invoice_num = ', '.join(invoices.mapped('name'))
            picking.invoice_number = invoice_num

                
    @api.constrains('driver_id')
    def _validate_driver_id(self):
        for record in self:
            if record.driver_id:
                # Assuming a simple mapping for demonstration purposes
                # In a real scenario, you might query a database or an external service
                if not record.driver_name or record.driver_name.isspace():
                    raise ValidationError("El nombre del conductor no puede estar vacío si se proporciona una cédula.")
                if not record.driver_id.isdigit() or len(record.driver_id) != 10:
                    raise ValidationError("La cédula del conductor debe contener exactamente 10 dígitos.")
                
    @api.constrains('driver_name')
    def _validate_driver_name(self):
        for record in self:
            if record.driver_name:
                # Assuming a simple mapping for demonstration purposes
                # In a real scenario, you might query a database or an external service
                if not record.driver_id or record.driver_id.isspace():
                    raise ValidationError("La cédula del conductor no puede estar vacía si se proporciona un nombre.")

    def _l10n_ec_edi_get_delivery_guide_values(self):
        '''
        Get the values to render the delivery guide XML template.
        '''
        self.ensure_one()
        return {
            'record': self,
            'l10n_ec_production_env': '2' if self.company_id.l10n_ec_production_env else '1',
            'l10n_ec_legal_name': self.company_id.l10n_ec_legal_name,
            'commercial_company_name': self.company_id.partner_id.commercial_company_name,
            'company_vat': self.company_id.partner_id.vat,
            'l10n_ec_authorization_number': self.l10n_ec_authorization_number,
            'l10n_ec_entity': self.picking_type_id.warehouse_id.l10n_ec_entity,
            'l10n_ec_emission': self.picking_type_id.warehouse_id.l10n_ec_emission,
            'sequence': self.l10n_ec_edi_document_number.split('-')[-1],
            'company_street': self.company_id.street,
            'warehouse_street': self.picking_type_id.warehouse_id.partner_id.street,
            'l10n_ec_transporter_name': self.l10n_ec_transporter_id.name,
            'l10n_ec_transporter_sri_code': self.l10n_ec_transporter_id._get_sri_code_for_partner().value,
            'l10n_ec_transporter_vat': self.l10n_ec_transporter_id.vat,
            'l10n_ec_forced_accounting': 'SI' if self.company_id.l10n_ec_forced_accounting else 'NO',
            'l10n_ec_special_taxpayer_number': self.company_id.l10n_ec_special_taxpayer_number,
            'l10n_ec_delivery_start_date': self.l10n_ec_delivery_start_date.strftime('%d/%m/%Y'),
            'l10n_ec_delivery_end_date': self.l10n_ec_delivery_end_date.strftime('%d/%m/%Y'),
            'l10n_ec_plate_number': self.l10n_ec_plate_number.replace('-', ''),
            'partner_vat': self.partner_id.commercial_partner_id.vat,
            'partner_name': self.partner_id.commercial_partner_id.name,
            'partner_address': self.partner_id._display_address().replace('\n', ' - '),
            'l10n_ec_transfer_reason': self.l10n_ec_transfer_reason,
            'lines': [{
                'product_barcode': line.product_id.barcode or line.product_id.default_code or 'N/A', # TODO: remove in master and keep main_code
                'main_code': line.product_id.barcode or line.product_id.default_code or 'N/A',
                'l10n_ec_auxiliary_code': line.product_id.l10n_ec_auxiliary_code or '',
                'product_partner_ref': line.product_id.with_context(lang=self.partner_id.lang).partner_ref,
                'qty_done': line.quantity,
                'lot_id': line.lot_id,
            } for line in self.mapped('move_line_ids_without_package')],
            'note': self.note.striptags().replace('\n', ' ')[:300] if self.note else None,
            'origin': self.origin or None,
        }