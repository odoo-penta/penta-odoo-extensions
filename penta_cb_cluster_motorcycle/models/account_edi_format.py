# -*- coding: utf-8 -*-
from odoo import models, _
from uuid import uuid4
from lxml import etree
import re
from odoo.addons.l10n_ec_edi.models.xml_utils import (
    NS_MAP,
    calculate_references_digests,
    cleanup_xml_signature,
    fill_signature,
)

from markupsafe import Markup
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'


    def _l10n_ec_generate_signed_xml(self, company_id, xml_node_or_string):
        # 1. Si estamos en ambiente demo, tomamos la ruta simplificada.
        if company_id._l10n_ec_is_demo_environment():
            xml_node_or_string = etree.tostring(
                xml_node_or_string,
                encoding='UTF-8',
                xml_declaration=True,
                pretty_print=True
            )
        else:
            # 2. Obtenemos el certificado
            certificate_sudo = company_id.sudo().l10n_ec_edi_certificate_id

            # 3. Preparamos los valores de la firma (Signature rendering)
            signature_id = f"Signature{uuid4()}"
            qweb_values = {
                'signature_id': signature_id,
                'signature_property_id': f'{signature_id}-SignedPropertiesID{uuid4()}',
                'certificate_id': f'Certificate{uuid4()}',
                'reference_uri': f'Reference-ID-{uuid4()}',
                'signed_properties_id': f'SignedPropertiesID{uuid4()}',
            }

            # 4. Añadimos información del certificado
            e, n = certificate_sudo._get_public_key_numbers_bytes()
            qweb_values.update({
                'sig_certif_digest': certificate_sudo._get_fingerprint_bytes(
                    hashing_algorithm='sha1',
                    formatting='base64'
                ).decode(),
                'x509_certificate': certificate_sudo._get_der_certificate_bytes().decode(),
                'rsa_modulus': n.decode(),
                'rsa_exponent': e.decode(),
                'x509_issuer_description': certificate_sudo._l10n_ec_edi_get_issuer_rfc_string(),
                'x509_serial_number': int(certificate_sudo.serial_number),
            })

            # 5. Parseamos el documento SIN llamar a cleanup_xml_node
            #    y limpiamos etiquetas con () vacíos en detAdicional
            if isinstance(xml_node_or_string, bytes):
                xml_node_or_string = xml_node_or_string.decode('utf-8')

            if isinstance(xml_node_or_string, str):
                # 🔧 Reemplazamos las etiquetas <detAdicional ...>()</detAdicional> por autoclosed <detAdicional .../>
                xml_node_or_string = re.sub(
                    r'<detAdicional([^>]*)>\(\)</detAdicional>',
                    r'<detAdicional\1/>',
                    xml_node_or_string
                )
                # Parseamos el string limpio a XML
                doc = etree.fromstring(xml_node_or_string.encode('utf-8'))
            else:
                # doc es un nodo lxml existente
                xml_str = etree.tostring(
                    xml_node_or_string,
                    encoding='UTF-8',
                    xml_declaration=False
                ).decode('utf-8')

                xml_str = re.sub(
                    r'<detAdicional([^>]*)>\(\)</detAdicional>',
                    r'<detAdicional\1/>',
                    xml_str
                )

                doc = etree.fromstring(xml_str.encode('utf-8'))

            # 6. Renderizamos la firma y la añadimos al documento
            signature_str = self.env['ir.qweb']._render('l10n_ec_edi.ec_edi_signature', qweb_values)
            signature = cleanup_xml_signature(signature_str)
            doc.append(signature)

            # 7. Calculamos digests y firmamos
            calculate_references_digests(signature.find('SignedInfo', namespaces=NS_MAP), base_uri='#comprobante')
            fill_signature(signature, certificate_sudo)

            # 8. Generamos la cadena final como bytes (sin usar short_empty_elements)
            xml_node_or_string = etree.tostring(
                doc,
                encoding='UTF-8',
                xml_declaration=True,
                pretty_print=True
            )

        # 9. Retornamos el XML como string
        xml_string = xml_node_or_string.decode('UTF-8')
        return xml_string

    def _l10n_ec_create_authorization_file_new(self, company_id, xml_string, authorization_number, authorization_date):
        # TODO master: merge with `_l10n_ec_create_authorization_file`
        xml_values = {
            'xml_file_content': Markup(xml_string[xml_string.find('?>') + 2:]),  # remove header to embed sent xml
            'mode': 'PRODUCCION' if company_id.l10n_ec_production_env else 'PRUEBAS',
            'authorization_number': authorization_number,
            'authorization_date': authorization_date.strftime(DTF),
        }

        # Renderizamos el XML base de autorización
        xml_response = self.env['ir.qweb']._render('l10n_ec_edi.authorization_template', xml_values)

        # 🔧 Aseguramos que el resultado sea una cadena válida
        if isinstance(xml_response, bytes):
            xml_response = xml_response.decode('utf-8')
        elif isinstance(xml_response, Markup):
            xml_response = str(xml_response)

        xml_response = xml_response.strip()

        # Limpieza personalizada: igual que cleanup_xml_node pero sin eliminar <detAdicional/>
        def safe_cleanup(node):
            """
            Recorre el árbol XML y elimina nodos vacíos,
            excepto los que no deben eliminarse (como detAdicional, campoAdicional, etc.)
            """
            for child in list(node):
                safe_cleanup(child)
                # Si el nodo no tiene texto ni hijos, eliminarlo excepto ciertos tags
                if (child.text is None or not child.text.strip()) and not len(child):
                    if child.tag in ['detAdicional', 'campoAdicional', 'detallesAdicionales']:
                        continue
                    node.remove(child)
            return node

        # Parseamos correctamente el XML y lo limpiamos
        xml_tree = etree.fromstring(xml_response.encode('utf-8'))
        xml_tree = safe_cleanup(xml_tree)

        # Retornamos el XML final como cadena unicode
        return etree.tostring(xml_tree, encoding='unicode')