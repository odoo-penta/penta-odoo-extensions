# -*- coding: utf-8 -*-
from . import tools_extra
import odoo.tools as odoo_tools
import logging
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)

# Inyeccion de funciones en el tootls
odoo_tools.remove_accents = tools_extra.remove_accents
odoo_tools.sanitize_text = tools_extra.sanitize_text
odoo_tools.extract_numbers = tools_extra.extract_numbers
odoo_tools.format_invoice_number = tools_extra.format_invoice_number
odoo_tools.xml_element = tools_extra.xml_element
odoo_tools.sanitize_text = tools_extra.sanitize_text
odoo_tools.split_doc_number = tools_extra.split_doc_number
odoo_tools.latam_id_code = tools_extra.latam_id_code
odoo_tools.doc_type_code = tools_extra.doc_type_code

def _run_sql_file(cr, module_name, relative_path):
    path = get_module_resource(module_name, relative_path)
    if not path:
        _logger.warning("No se encontró el archivo SQL: %s/%s", module_name, relative_path)
        return
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    cr.execute(sql)
    _logger.info("SQL aplicado desde: %s", path)

def post_init_hook(env):
    """Se ejecuta después de instalar/actualizar el módulo (Odoo >=16 usa env)."""
    cr = env.cr
    _logger.info("Instalando funciones SQL de l10n_ec_penta_base…")
    _run_sql_file(cr, "l10n_ec_penta_base", "sql/purchase_report.sql")
    _logger.info("Funciones SQL de l10n_ec_penta_base instaladas.")