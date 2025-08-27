# -*- coding: utf-8 -*-
from . import tools_extra
import odoo.tools as odoo_tools

# Inyeccion de funciones en el tootls
odoo_tools.remove_accents = tools_extra.remove_accents
odoo_tools.sanitize_text = tools_extra.sanitize_text
odoo_tools.extract_numbers = tools_extra.extract_numbers