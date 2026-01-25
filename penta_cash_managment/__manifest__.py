{
    'name': 'Penta Cash Managment',
    'version': '18.0.0.0',
    'category': 'Pagos',
    'description': u"""
Produce reports in txt format according to the bank's structure
""",
    'depends': ['account','account_accountant'],
    'author': 'Pentalab',
    'license': 'LGPL-3',
    "data":[
        "security/ir.model.access.csv",
        #Data
        "data/penta.cash.managment.bank.csv",
        #Views
        "views/account_journal_from.xml",
        "views/account_batch_payment_from.xml",
        "views/batch_payment_popup_wizard.xml",
    ],
    'installable': True,
    'application': False,
}