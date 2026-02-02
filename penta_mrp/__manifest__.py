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
    'name': "Custom MRP - Penta",
    'summary': "Penta manufacturing customizations.",
    'description': """
        Improve labor input in minutes.
    """,
    'author' : 'PentaLab',
    'maintainer': 'PentaLab',
    'contributors': [
        'AntonyPineda <vini16.av@gmail.com>',
    ],
    'website': "https://pentalab.tech/",
    'license': 'OPL-1',
    'category': 'Manufacturing',
    'version': '18.0.0.1.0',
    'depends': ['cost_standard_eljuri'],
    'data': [
        'reports/report_cost_analysis.xml',
        'reports/report_cost_analysis_templates.xml',
        
        'views/mrp_operation_views.xml',
        'views/mrp_routing_views.xml',
        'views/mrp_bom_views.xml',
        'views/product_template_views.xml',
        'views/mrp_maintenance_views.xml',
    ],
    'installable': True,
    'application': True,
    
}
