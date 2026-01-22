from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import tempfile
import os
import unicodedata

class BatchPaymentPopupWizardModel(models.TransientModel):
    _name = 'batch.payment.popup.wizard'
    _description = 'Popup Wizard for Batch Payment'

    batch_payment_id = fields.Many2one("account.batch.payment", string="Referencia")
    journal_id = fields.Many2one("account.journal", string="Journal")
    
    bank_format_ids = fields.Many2many(
        "penta.cash.managment.bank",
        string="Bancos soportados"
    )

    bank_format_id = fields.Many2one(
        "penta.cash.managment.bank",
        string="Banco / formato"
    )

    def generate_report(self):
        # Obtén el formato seleccionado
        selected_format = self.bank_format_id
        selected_batch_payment = self.batch_payment_id

        if not selected_format:
            raise UserError('Debe seleccionar un formato para generar el informe.')
        else:
            if selected_format.code == 'austro_hr':
                return self.report_austro(selected_batch_payment)
            else:
                raise UserError('Contactese con Pentalab para un Reporte de Banco')
            
        



    def report_austro(self,selected_batch_payment):
        # Inicializa la variable content
        content = ""

        # Realiza una búsqueda en el modelo account.payment
        account_payments = self.env['account.payment'].search([('batch_payment_id', '=', selected_batch_payment.id)])

        # Si existen pagos, añadir cada uno al contenido
        if account_payments:
            for account_payment in account_payments:
                
                type_payment=self.type_payment(account_payment)

                #Diccionario de Datos
                customer_type_mapping = {
                    'Cédula': 'C',      # Cédula -> C
                    'RUC': 'R',         # RUC -> R
                    'Pasaporte': 'P'    # Pasaporte -> P
                }

                type_customer=self.type_customer(account_payment,customer_type_mapping)

                customer_id=self.customer_id(account_payment)

                customer_name=self.customer_name(account_payment)

                type_account=self.type_account(account_payment)

                partner_bank_id=self.partner_bank_id(account_payment)

                partner_bank_currency_name=self.partner_bank_currency_name(account_payment)

                bank_id=self.bank_id(account_payment)

                amount_signed=self.amount_signed(account_payment)

                # Agregar la información del pago al contenido, separados por tabuladores
                content += f"{type_payment}\t{type_customer}\t{customer_id}\t{customer_id}\t{customer_name}\t{type_account}\t{partner_bank_id}\t{partner_bank_currency_name}\t{amount_signed}\t{bank_id}\n"
        else:
            content += "No hay pagos relacionados con este batch payment.\n"
        
        # Llamar al método para generar y adjuntar el archivo
        return self.generate_file_attachment(content, "report_austro.txt")

    def type_payment(self,account_payment):
        # Revisión del tipo de pago para agregar el texto adecuado
        if not account_payment.payment_type:
            type_payment = " "
        else:
            if account_payment.payment_type == 'outbound':
                type_payment = "PA"
            elif account_payment.payment_type == 'inbound':
                type_payment = "CO"
            else:
                type_payment = account_payment.payment_type  # Otro tipo de pago
        
        return type_payment
    
    def type_customer(self,account_payment,customer_type_mapping):

        customer = account_payment.partner_id.l10n_latam_identification_type_id
        customer_name = customer.name if customer else ""
        country_id = customer.country_id.id if customer else None
        # Inicializa el valor por defecto
        type_id_customer = " "
        
        # Validar si el país es el correcto y el tipo de identificación está en el diccionario
        if country_id == 63 and customer_name in customer_type_mapping:
            type_id_customer = customer_type_mapping[customer_name]

        return type_id_customer
    
    def customer_id(self,account_payment):
        customer_id = account_payment.partner_id.vat
        if not customer_id:
            customer_id = " "
        return customer_id
    
    def customer_name(self,account_payment):
        customer_name = account_payment.partner_id.name
        if not customer_name:
            customer_name = " "
        else:
            customer_name = customer_name.upper()
            # Eliminar tildes (normalizar en forma NFKD y filtrar caracteres de acento)
            customer_name = ''.join(
                (c for c in unicodedata.normalize('NFKD', customer_name) if not unicodedata.combining(c))
            )

            # Reemplazar la ñ con un guion
            customer_name = customer_name.replace('Ñ', '-')

        return customer_name
    
    def type_account(self,account_payment):
        try:
            # Intenta obtener el valor del campo
            type_account = account_payment.partner_bank_id.account_type
            if type_account=='ahorros':
                type_account="AHO"
            elif type_account=='corriente':
                type_account="CTE"
        except AttributeError:
            # Si no existe el campo, asigna un valor por defecto
            type_account = " "

        return type_account

    def partner_bank_id(self,account_payment):
        partner_bank_id = account_payment.partner_bank_id.acc_number
        if not partner_bank_id:
            partner_bank_id = " "
        return partner_bank_id
    
    
    def amount_signed(self,account_payment):
        amount_signed = abs(account_payment.amount_signed)

        # Convierte el valor a string y se asegura de que tenga dos decimales
        amount_str = f"{amount_signed:.2f}"

        # Elimina la coma y convierte el número a un entero multiplicado por 100
        formatted_amount = amount_str.replace('.', '')
        formatted_amount=formatted_amount.zfill(13)

        return formatted_amount
    
    def partner_bank_currency_name(self,account_payment):
        partner_bank_currency_name = account_payment.currency_id.name
        if not partner_bank_currency_name:
            partner_bank_currency_name = " "
        return partner_bank_currency_name
    
    def bank_id(self,account_payment):
        bank_id = account_payment.partner_bank_id.bank_id.bic
        if not bank_id:
            bank_id = " "
        # Convertir a string por si es un número, y completar con ceros a la izquierda si la longitud es menor a 4
        bank_id = str(bank_id).zfill(4)
        return bank_id


    def generate_file_attachment(self, content, file_name):
        """
        Método para crear un archivo temporal con el contenido dado y adjuntarlo al modelo.

        Args:
        - content: El contenido que se va a escribir en el archivo.
        - file_name: El nombre del archivo.

        Returns:
        - dict: Una acción para descargar el archivo generado.
        """

        # Crea un archivo temporal para el reporte
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp_file:
            tmp_file.write(content.encode('utf-8'))
            tmp_file_path = tmp_file.name

        # Crea un adjunto para el reporte
        with open(tmp_file_path, 'rb') as file:
            file_data = file.read()
            file_data_base64 = base64.b64encode(file_data).decode('utf-8')

        attachment_id = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': file_data_base64,
            'res_model': 'batch.payment.popup.wizard',
            'res_id': self.id,
        })

        # Obtener la URL base
        base_url = self.env['ir.config_parameter'].search([('key', '=', 'web.base.url')])

        # Preparar la URL para la descarga del archivo
        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'

        # Retornar la acción para descargar el archivo
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url.value) + str(download_url),
            "target": "new",
        }
            