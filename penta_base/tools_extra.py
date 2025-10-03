# -*- coding: utf-8 -*-
import re
import unicodedata


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