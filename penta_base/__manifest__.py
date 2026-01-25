# -*- coding: utf-8 -*-
#################################################################################
# Author      : PentaLab (<https://pentalab.tech>)
# Copyright(c): 2025
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it..
#
#################################################################################

{
    "name": "Penta Base",
    'summary': 'Validations and global methods',
    'description': """
        Add useful and reusable methods throughout the system.
    """,
    'author': 'PentaLab',
    'maintainer': 'PentaLab',
    'contributors': ['AntonyPineda <vini16.av@gmail.com>'],
    'website': 'https://pentalab.tech/',
    'license': 'OPL-1',
    'category': 'Tools/Tools',
    'version': '18.0.0.1',
    'depends': [
        'base', 'purchase', 'stock', 'account'
    ],
    'data': [
    ],
    'demo': [
    ],
    "post_init_hook": "post_init_hook",
    'installable': True,
    "auto_install": True,
    'application': False,
}
