# -*- coding: utf-8 -*-
import re
import unicodedata
import pytz
from lxml import etree
from datetime import datetime

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

def month_name_es(month_number):
    """Devuelve el nombre del mes en español dado su número (1-12)."""
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
        7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    return meses.get(int(month_number), "")

def local_tz(record, dt):
    """Convierte un datetime UTC a la zona horaria del usuario."""
    if not dt:
        return ''

    tz_name = getattr(record.partner_id, "tz", None) or record.env.user.tz or "UTC"
    try:
        user_tz = pytz.timezone(tz_name)
    except Exception:
        user_tz = pytz.UTC

    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)

    local_dt = dt.astimezone(user_tz)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")

def split_amount(amount):
    """Divide un monto decimal en parte entera y decimal."""
    integer_part = int(amount)
    decimal_part = int(round((amount - integer_part) * 100))
    return integer_part, decimal_part
