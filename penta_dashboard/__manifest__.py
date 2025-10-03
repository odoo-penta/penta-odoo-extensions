{
    'name': 'PENTA Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Customizable dashboard for PENTA users',
    'author': 'Odoo PENTA',
    'website': 'https://github.com/odoo-penta',
    'depends': ['base', 'web', 'penta_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'penta_dashboard/static/src/js/dashboard.js',
            'penta_dashboard/static/src/css/dashboard.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
