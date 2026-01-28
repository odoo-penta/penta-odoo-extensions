# /tu_modulo/__manifest__.py
{
    'name': 'Penta Documentos Electronicos',
    'version': '18.0.0.0.1',
    'category': 'Tools',
    'summary': 'Módulo para subir y gestionar archivos de texto para facturas de proveedor',
    'author': 'Pentalab',
    'license': 'LGPL-3',
    'depends': ['base','stock'],
    'data': [
        'security/archivo_model_rule.xml',
        'security/ir.model.access.csv',
        'views/popup_view.xml',
        'views/archivo_view.xml',
        'views/account_move_views.xml',
        'data/advance_docs_data.xml'
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
}
