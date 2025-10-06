{
    'name': 'PENTA Mail Integration',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Advanced email integration and templates',
    'author': 'Odoo PENTA',
    'website': 'https://github.com/odoo-penta',
    'depends': ['base', 'mail', 'penta_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/mail_template_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
