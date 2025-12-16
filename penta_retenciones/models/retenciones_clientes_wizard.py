# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError

class RetencionClientesWizard(models.TransientModel):
    _name = 'retencion.clientes.wizard'
    _description = 'Wizard para gestionar retenciones de clientes'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Cliente',
        required=True
    )
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Diario',
        required=True
    )
    document_number = fields.Char(
        string='Número de Documento',
        required=True
    )
    sri_authorization = fields.Char(
        string='Autorización SRI'
    )

    retencion_line_ids = fields.One2many(
        comodel_name='retencion.clientes.wizard.line',
        inverse_name='wizard_id',
        string='Líneas de Retención'
    )

    # -------------------------------------------------------------------------
    # 1) Validación de la longitud de sri_authorization (10, 42 o 49)
    # -------------------------------------------------------------------------
    @api.constrains('sri_authorization')
    def _check_sri_authorization_length(self):
        for wizard in self:
            if wizard.sri_authorization:
                length = len(wizard.sri_authorization.strip())
                if length not in (10, 42, 49):
                    raise ValidationError(
                        "El número de Autorización es incorrecto. "
                        "Debe tener 10, 42 o 49 dígitos, no %s." % length
                    )

    # -------------------------------------------------------------------------
    # 2) Formatear document_number como 001-001-123456789 al cambiar el valor
    # -------------------------------------------------------------------------
    @api.onchange('document_number')
    def _onchange_document_number(self):
        """Auto-completa el número de documento a formato 3-3-9 dígitos.
           Ej: '1-2-23' => '001-002-000000023'
        """
        if self.document_number:
            parts = self.document_number.split('-')
            if len(parts) == 3:
                p1, p2, p3 = parts
                # Quitamos espacios y completamos con ceros
                p1 = p1.strip().zfill(3)
                p2 = p2.strip().zfill(3)
                p3 = p3.strip().zfill(9)

                # Verificamos que sean solo dígitos
                if not (p1.isdigit() and p2.isdigit() and p3.isdigit()):
                    raise UserError(
                        "El número de Documento debe contener solo dígitos "
                        "en cada segmento. Ejemplo: 001-001-123456789"
                    )
                # Asignamos de nuevo con el formato correcto
                self.document_number = f'{p1}-{p2}-{p3}'
            else:
                # Si no trae 3 partes, puedes decidir si limpias o lanzas error
                # Aquí lanzamos un error para forzar el formato
                raise UserError(
                    "Formato inválido. Debe ser 3-3-9 dígitos. "
                    "Ejemplo: 001-001-123456789"
                )

    def action_confirm(self):
        self.ensure_one()

        # 1) Crear la factura (move) como "out_invoice" sin líneas
        move = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
            'date': self.date,
            'partner_id': self.partner_id.id,
            'invoice_date': self.date,
            'l10n_ec_withhold_date':self.date,
            'invoice_origin': self.document_number,
            'ref': self.document_number or '',
            'currency_id': self.journal_id.currency_id.id 
                  or self.env.company.currency_id.id,
            'l10n_ec_authorization_number':self.sri_authorization
        })

        # 2) Crear las líneas de retención, pasándoles el move_id
        withhold_lines_vals = []
        for line in self.retencion_line_ids:
            # Validar que el impuesto esté bien configurado
            if not line.tax_id or not line.tax_id.invoice_repartition_line_ids:
                raise UserError(
                    "El impuesto '%s' no está correctamente configurado."
                    % (line.tax_id.name if line.tax_id else '')
                )

            # Si existe cuenta base configurada a nivel de compañía, se usa
            base_account = self.env.company.l10n_ec_tax_base_sale_account_id
            if base_account:
                account_id = base_account.id
            else:
                # Si no hay cuenta base, se intenta con la del impuesto
                repartition_line = line.tax_id.invoice_repartition_line_ids.filtered(lambda r: r.account_id)
                if not repartition_line:
                    raise UserError(
                        "El impuesto '%s' no tiene cuenta contable configurada."
                        % line.tax_id.name
                    )
                account_id = repartition_line[0].account_id.id

            # Agregar línea contable de retención
            withhold_lines_vals.append((0, 0, {
                'move_id': move.id,
                'name': f'Retención {line.tax_id.name}',
                'account_id': account_id,
                'credit': line.base_amount,
                'debit': 0.0,
                'tax_ids': [(6, 0, [line.tax_id.id])],
            }))

            
        # 3) Actualizar el movimiento con las líneas de retención
        move.write({'l10n_ec_withhold_line_ids': withhold_lines_vals})
        document_type = self.env['l10n_latam.document.type'].search([('code', '=', '07')], limit=1)
        if not document_type:
            raise UserError("No se encontró un tipo de documento LATAM con el código '07'.")
        # 4) Activar l10n_latam_use_documents en True
        move.write({
            'l10n_latam_use_documents': True,
            'l10n_latam_document_type_id': document_type.id,
        })
        

        # 7) Verificar las líneas contables resultantes
        print("Líneas contables ajustadas:")
        for line in move.l10n_ec_withhold_line_ids:
            move.line_ids.create({'move_id': move.id,
                    'name': line.name,
                    'account_id': line.account_id.id,
                    'debit': line.credit,
                    'credit': 0.0})
            
        for line in move.line_ids:
            if line.name == "Balance automático de línea":  # Verifica si la etiqueta coincide
                try:
                    # Intenta cambiar el account_id a un nuevo valor
                    nuevo_account_id = self.journal_id.account_withhold.id  # Reemplaza con el ID de la cuenta deseada
                    line.account_id = nuevo_account_id
                    line.write({'account_id': nuevo_account_id})  # Guarda el cambio en la base de datos
                    print(f"Se actualizó el account_id de la línea: {line.name}")
                except Exception as e:
                    print(f"No se pudo actualizar el account_id de la línea: {line.name}. Error: {e}")



        # 8) Retornar la acción para abrir la factura en vista formulario
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }



    def action_close(self):
        """Cierra el wizard sin hacer nada."""
        return {'type': 'ir.actions.act_window_close'}


class RetencionClientesWizardLine(models.TransientModel):
    _name = 'retencion.clientes.wizard.line'
    _description = 'Líneas de retención en el wizard de retenciones de clientes'

    wizard_id = fields.Many2one(
        comodel_name='retencion.clientes.wizard',
        string='Wizard Padre'
    )
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Impuesto',
        required=True
    )
    base_amount = fields.Float(
        string='Base',
        required=True
    )
    tax_amount = fields.Float(
        string='Monto de Retención',
        required=True
    )

    @api.onchange('base_amount', 'tax_id')
    def _onchange_calcular_tax_amount(self):
        """Calcula automáticamente tax_amount = base_amount * (porcentaje/100)
           si el tax está configurado como 'percent'. 
        """
        for line in self:
            # Si existe un tax y es de tipo "porcentaje"
            if line.tax_id and line.tax_id.amount_type == 'percent':
                porcentaje = line.tax_id.amount  # Ejemplo: 20 => 20%
                line.tax_amount = abs(line.base_amount * (porcentaje / 100.0))
            else:
                # Si no es 'percent' u otro caso, se podría dejar en 0 o en base_amount
                # según tu lógica
                line.tax_amount = 0.0
