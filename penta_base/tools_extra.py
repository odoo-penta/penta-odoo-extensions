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