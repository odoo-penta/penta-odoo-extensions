# -*- coding: utf-8 -*-
###############################################################################
# Author      : Pentalab (<https://pentalab.tech>)
# Copyright(c): 2025
###############################################################################
# All Rights Reserved.
#
# This module is copyright property of the autor mentioned above.
# You can't redistribute it and/or modify it.
#
###############################################################################
{
    'name': 'Penta Kardex',
    'version': '18.0.1.0.0',
    'summary': 'Kardex de productos',
    'description': 'Módulo para generar reportes de kardex detallados de productos.',
    'author': 'Pentalab',
    'website': 'https://pentalab.tech',
    'category': 'Inventory/Reporting',
    'depends': ['base','stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_actions_server.xml',
        'views/report_kardex.xml',
        'views/report.xml',
        'views/kardex_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
