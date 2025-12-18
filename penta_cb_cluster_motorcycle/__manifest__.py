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
    'description': """
        This module implements vehicle data into products, purchases and sales
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
    'version': '18.0.0.0',
    'depends': [
        'penta_base',
        'product',
        'account_accountant',
        'l10n_ec_edi',
        'import_module',
        'account',
        'sale_management',
    ],
    'data': [
        "security/ir.model.access.csv",
        "data/edi_document.xml",
        'wizard/import_picking_operations.xml',
        'views/view_country_state_tree_inherit.xml',
        'views/view_out_invoice_tree_inherit.xml',
        'views/stock_lot_views.xml',
        'views/stock_move_views.xml',
        'views/stock_picking_views.xml',
        'views/product_views.xml',
        'views/view_account_tax_inherit.xml',
        'views/account_move_stock.xml',
        'views/report_invoice.xml',
        'views/stock_lot_plate_view.xml',
        'views/project_task.xml',
        'views/project_wizard.xml',
        
    ],
    'installable': True,
    'application': False,
}