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
    "name": "Check printing - Penta",
    "summary": "Check printing with editable checks",
    'description': """
        Print editable checks from the system
    """,
    'author': 'PentaLab',
    'maintainer': 'PentaLab',
    'contributors': ['AntonyPineda <vini16.av@gmail.com>'],
    'website': 'https://pentalab.tech/',
    'license': 'OPL-1',
    "category": "Accounting",
    "version": "18.0.0.0.0",
    "depends": [
        "account",
        "account_check_printing",
    ],
    "data": [
        'data/default_formats.xml',
        
        'security/ir.model.access.csv',
        
        'report/check_penta_report.xml',
        "report/check_penta_template.xml",
        
        'views/check_format_views.xml',
        'views/account_journal_views.xml',
        'views/res_config_settings_views.xml',
    ],
    "installable": True,
    "application": True,
}
