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
    'name': "Account Credit sales",
    'summary': "Generate amortization tables for credit sales based on financing reward programs.",
    'description': """
    This module extends Odoo Sales to support credit sales with automatic amortization schedules.
    """,
    'author': "PentaLab",
    'contributors': [
        'AntonyPineda <vini16.av@gmail.com>'
    ],
    'website': "https://pentalab.tech/",
    'category': 'Accounting',
    'version': '18.0.1.0.0',
    'depends': [
        'l10n_ec_account_penta',
        'loyalty',
    ],
    'data': [
        'security/ir.model.access.csv',
        
        'views/account_move_views.xml',
        'views/account_payment_term_views.xml',
        'views/loyalty_reward_views.xml',
        'views/loyalty_rule_views.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'license': 'OPL-1',
}

