# -*- coding: utf-8 -*-
import re
import unicodedata
from lxml import etree


def remove_accents(text):
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    )
    
def sanitize_text(text):
    if not text:
        return ''
    # Quitar tildes
    text = remove_accents(text)
    # Quitar guiones y caracteres especiales (mantener letras, números y espacios)
    text = re.sub(r'[^A-Za-z0-9\s]', '', text)
    # Convertir a mayúsculas
    return text.upper().strip()

def extract_numbers(text):
    if not text:
        return ''
    # Extraer solo los dígitos
    return re.sub(r'\D', '', text)

def format_invoice_number(text):
    # Da formato 000-000-00000000
    digits = extract_numbers(text)
    # Rellenar con ceros a la derecha hasta 14 dígitos
    if len(digits) <= 3:
        return digits
    elif len(digits) <= 6:
        return f"{digits[:3]}-{digits[3:]}"
    else:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"

def xml_element(parent , tag, text=None, **attrs):
        """Helper para crear un elemento XML con atributos opcionales y texto."""
        el = etree.SubElement(parent, tag, **{k: str(v) for k, v in attrs.items() if v is not None})
        if text is not None:
            el.text = str(text)
        return el

def split_doc_number(doc):
    """'001-002-000000123' -> ('001','002','000000123') con tolerancia."""
    if not doc:
        return "", "", ""
    s = str(doc)
    est = s[0:3] if len(s) >= 3 else ""
    pto = s[4:7] if len(s) >= 7 else ""
    num = s[8:]  if len(s) >= 9 else ""
    return est, pto, num

def latam_id_code(partner):
    """Mapea el tipo de identificación del partner a {C,P,R}."""
    it = partner.l10n_latam_identification_type_id
    if not it:
        return ""
    code = (getattr(it, "code", "") or "").lower()
    name = (it.name or "").lower()
    if code in ("cedula", "national_id", "dni") or "cedula" in name or "cédula" in name:
        return "C"
    if code in ("passport", "pasaporte") or "pasaporte" in name:
        return "P"
    if code in ("ruc", "tax_id") or "ruc" in name:
        return "R"
    return ""

def doc_type_code(latam_doc_type):
    """Obtiene el código del tipo de comprobante."""
    if not latam_doc_type:
        return ""
    for attr in ("l10n_ec_code", "code", "internal_code"):
        val = getattr(latam_doc_type, attr, None)
        if val:
            return str(val)
    return ""

def remove_control_characters(byte_node):
    """
    The characters to be escaped are the control characters #x0 to #x1F and #x7F (most of which cannot appear in XML)
    [...] XML processors must accept any character in the range specified for Char:
    `Char	   :: =   	#x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]`
    source:https://www.w3.org/TR/xml/
    """
    return re.sub(
        '[^'
        '\u0009'
        '\u000A'
        '\u000D'
        '\u0020-\uD7FF'
        '\uE000-\uFFFD'
        '\U00010000-\U0010FFFF'
        ']'.encode(),
        b'',
        byte_node,
    )

def cleanup_xml_node(xml_node_or_string, remove_blank_text=True, remove_blank_nodes=True, indent_level=0, indent_space="  "):
    """Clean up the sub-tree of the provided XML node.

    If the provided XML node is of type:
    - etree._Element, it is modified in-place.
    - string/bytes, it is first parsed into an etree._Element
    :param xml_node_or_string (etree._Element, str): XML node (or its string/bytes representation)
    :param remove_blank_text (bool): if True, removes whitespace-only text from nodes
    :param remove_blank_nodes (bool): if True, removes leaf nodes with no text (iterative, depth-first, done after remove_blank_text)
    :param indent_level (int): depth or level of node within root tree (use -1 to leave indentation as-is)
    :param indent_space (str): string to use for indentation (use '' to remove all indentation)
    :returns (etree._Element): clean node, same instance that was received (if applicable)
    """
    xml_node = xml_node_or_string
    # Convert str/bytes to etree._Element
    if isinstance(xml_node, str):
        xml_node = xml_node.encode()  # misnomer: fromstring actually reads bytes
    if isinstance(xml_node, bytes):
        parser = etree.XMLParser(recover=True, resolve_entities=False)
        xml_node = etree.fromstring(remove_control_characters(xml_node), parser=parser)

    # Process leaf nodes iteratively
    # Depth-first, so any inner node may become a leaf too (if children are removed)
    def leaf_iter(parent_node, node, level):
        for child_node in node:
            leaf_iter(node, child_node, level if level < 0 else level + 1)

        # Indentation
        if level >= 0:
            indent = '\n' + indent_space * level
            if not node.tail or not node.tail.strip():
                node.tail = '\n' if parent_node is None else indent
            if len(node) > 0:
                if not node.text or not node.text.strip():
                    # First child's indentation is parent's text
                    node.text = indent + indent_space
                last_child = node[-1]
                if last_child.tail == indent + indent_space:
                    # Last child's tail is parent's closing tag indentation
                    last_child.tail = indent
        
        # Removal condition: node is leaf (not root nor inner node)
        if parent_node is not None and len(node) == 0:
            if remove_blank_text and node.text is not None and not node.text.strip():
                # node.text is None iff node.tag is self-closing (text='' creates closing tag)
                node.text = ''
                print("Entro op1")
            if remove_blank_nodes and not (node.text or ''):
                parent_node.remove(node)
                print("Entro op2")

    leaf_iter(None, xml_node, indent_level)
    return xml_node
