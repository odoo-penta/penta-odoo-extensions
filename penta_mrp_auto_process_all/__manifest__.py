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
    'version': '18.0.2.1.0',
    'depends': ['mrp'],
    'data': [
        "data/ir_sequence_data.xml",
        
        'security/ir.model.access.csv',
        
        'wizard/produce_line_wizard_view.xml',
        
        "views/res_config_settings_views.xml",
        'views/mrp_view.xml',
        'views/product_views.xml',
        "views/stock_lot_views.xml",
        "views/sri_motor_subclass_views.xml",
        "views/wizard_views.xml",
    ],
    'installable': True,
    'application': True,
    
}
