{
    'name': 'Extended Remission',
    'version': '1.1',
    'summary': 'Adds extra fields to the remission document.',
    'description': """
        This module adds the following fields to the remission document:
        - Driver's Name
        - Driver's ID
    """,
    'author': 'David Pineda',
    'license': 'LGPL-3',
    'depends': ['stock', 'l10n_ec', 'l10n_ec_edi_stock'],
    'data': [
        'views/remission_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
