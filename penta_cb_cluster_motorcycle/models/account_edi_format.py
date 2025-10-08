# -*- coding: utf-8 -*-
from odoo import models, _
from uuid import uuid4
from lxml import etree
import re
from odoo.addons.l10n_ec_edi.models.xml_utils import (
    NS_MAP,
    calculate_references_digests,
    fill_signature,
)
from odoo.addons.penta_cb_cluster_motorcycle.models.xml_utils import cleanup_xml_signature


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
            #    Nota: Para poder hacer la sustitución con re.sub, convertimos a string y luego
            #    volvemos a parsearlo. Si xml_node_or_string es bytes, lo decodificamos a str.
            if isinstance(xml_node_or_string, bytes):
                xml_node_or_string = xml_node_or_string.decode('utf-8')

            if isinstance(xml_node_or_string, str):
                # a) Realizamos la sustitución en el string con la expresión regular
                xml_node_or_string = re.sub(r'>\(\)</detAdicional>', '/>', xml_node_or_string)
                # b) Parseamos el string resultante a objeto lxml
                doc = etree.fromstring(xml_node_or_string.encode('utf-8'))
            else:
                # doc es un nodo lxml existente
                # Lo convertimos a string
                xml_str = etree.tostring(xml_node_or_string, encoding='UTF-8', xml_declaration=False).decode('utf-8')
                
                # Hacemos la sustitución
                xml_str = re.sub(r'>\(\)\s*</detAdicional>', r'/>', xml_str)
                
                # Volvemos a parsear a un nodo lxml
                doc = etree.fromstring(xml_str.encode('utf-8'))

            
            # 6. Renderizamos la firma y la añadimos al documento
            signature_str = self.env['ir.qweb']._render('l10n_ec_edi.ec_edi_signature', qweb_values)
            # Asumiendo que cleanup_xml_signature es una función que debes mantener
            signature = cleanup_xml_signature(signature_str)
            doc.append(signature)

            # 7. Calculamos digests y firmamos (métodos existentes en tu implementación original)
            calculate_references_digests(signature.find('SignedInfo', namespaces=NS_MAP), base_uri='#comprobante')
            fill_signature(signature, certificate_sudo)

            # 8. Generamos la cadena final como bytes
            xml_node_or_string = etree.tostring(
                doc,
                encoding='UTF-8',
                xml_declaration=True,
                pretty_print=True
            )

        # 9. Retornamos el XML como string
        xml_string = xml_node_or_string.decode('UTF-8')
        return xml_string
    