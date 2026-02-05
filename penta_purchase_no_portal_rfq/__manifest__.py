# -*- coding: utf-8 -*-
#################################################################################
# Author      : PentaLab (<https://pentalab.tech>)
# Copyright(c): 2025
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
{
    "name": "Penta Correo sin cotizacion",
    "summary": "Elimina acceso portar de cotización",
    "description": """
        Al enviar correo al proveedor de cotizacion no muestra boton de Ver cotizacion (Portal).
    """,
    'author': 'PentaLab',
    'maintainer': 'PentaLab',
    'contributors': ['AntonyPineda <vini16.av@gmail.com>'],
    'website': 'https://pentalab.tech/',
    "license": "LGPL-3",
    'category': 'Uncategorized',
    "version": "18.0.0.0.1",
    "depends": [
        'sale_management',
    ],
    "data": [
        'views/sale_portal_templates.xml',
    ],
    "installable": True,
    "application": False,
}
