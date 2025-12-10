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
    'name': "Multi Production Without Backorder All",
    'summary': "Multi Lot serial production without backorder.This feature allows you to auto process of consume lines without backorder from same wizard.",
    'description': """
        Multi Lot serial production without backorder.This feature allows you to auto process of consume lines without backorder from same wizard.
    """,
    'author' : 'PentaLab',
    'maintainer': 'PentaLab',
    'contributors': [
        'AntonyPineda <vini16.av@gmail.com>',
    ],
    'website': "https://pentalab.tech/",
    'license': 'OPL-1',
    'category': 'Manufacturing',
    'version': '18.0.0.0',
    'depends': ['mrp'],
    'data': [
        'security/ir.model.access.csv',
        
        'wizard/produce_line_wizard_view.xml',
        
        'views/mrp_view.xml',
    ],
    'installable': True,
    'application': True,
    
}
