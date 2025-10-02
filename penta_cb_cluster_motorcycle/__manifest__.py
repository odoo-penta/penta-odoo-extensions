# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'XML Invoice',
    'version': '18.0.0.1',
    'summary': 'XML generation for invoices',
    'sequence': 10,
    'description': """
Generate XML files for invoices.
==================================================================================
This module allows you to generate XML files for invoices.""",
    'category': 'Accounting/Accounting',
    'website': 'https://www.pentalab.odoo.com/',
    'author': 'Pentalab',
    'maintainer': 'Pentalab',
    'copyright': '© 2025 Pentalab',
    'contributors': [
        'Bernardo Bustamante <bbustamante@pentalab.tech>'
        ],
    'depends': ['base', 'account_accountant'],
    'data': [
        'views/view_out_invoice_tree_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}