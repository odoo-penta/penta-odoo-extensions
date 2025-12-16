{
    'name': 'Pentalab Retenciones',
    'sumary':'Pentalab Retenciones',
    'version': '18.0.0.0',
    'author': 'Pentalab',
    'license': 'LGPL-3',
    'category': 'Development',
    'description': u"""
Retenciones de clientes
""",
    'depends': ['base','account'],
    'data':[
        'views/retenciones_clientes_wizard_views.xml',
        'views/account_journal_inherit_view.xml',
        'views/retenciones_clientes.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'auto_install': False,

}