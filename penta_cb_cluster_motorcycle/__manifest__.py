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
    'name': 'Vehicle Data Integration',
    'summary': 'Integrates vehicle information into products',
    'version': '18.0.0.1',
    'description': """
        This module implements vehicle data into products, purchases and sales.
    """,
    'author': 'PentaLab',
    'maintainer': 'PentaLab',
    'contributors': [
        'AntonyPineda <vini16.av@gmail.com>',
        'Bernardo Bustamante <bbustamante@pentalab.tech>'
    ],
    'website': 'https://pentalab.tech/',
    'license': 'OPL-1',
    'category': 'Accounting/Accounting',
    'depends': [
        'penta_base',
        'product',
        'account_accountant'
    ],
    'data': [
        "security/ir.model.access.csv",
        
        'wizard/import_picking_operations.xml',
        
        'views/view_out_invoice_tree_inherit.xml',
        'views/stock_lot_views.xml',
        'views/stock_move_views.xml',
        'views/stock_picking_views.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
}