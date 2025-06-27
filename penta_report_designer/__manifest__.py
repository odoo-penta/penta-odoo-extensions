{
    'name': 'PENTA Report Designer',
    'version': '18.0.1.0.0',
    'category': 'Reporting',
    'summary': 'Advanced report designer and templates',
    'author': 'Odoo PENTA',
    'website': 'https://github.com/odoo-penta',
    'depends': ['base', 'web', 'penta_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/report_designer_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'penta_report_designer/static/src/js/report_designer.js',
            'penta_report_designer/static/src/css/report_designer.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
