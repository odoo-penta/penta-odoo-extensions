{
    'name': 'Import Module.',
    'sumary':'Modulo de importaciones Pentalab',
    'version': '18.0.0.0.1',
    'author': 'Pentalab',
    'license': 'LGPL-3',
    'depends': ['base','account','purchase','stock','account_accountant','stock_landed_costs','stock_account'],
    'data':[
        "security/ir.model.access.csv",
        #Data
        "data/action_create_landed_cost.xml",
        # "data/scheduled_actions.xml"
        # "data/cron_data.xml"
        #Views
        "views/views.xml",
        "views/menus.xml",
        "views/form.xml",
        "views/res_config_settings_views.xml",
        "views/purchase_order.xml",
        "views/account_move.xml",
        "views/account_payment.xml",
        "views/stock_landed_cost.xml",
        "security/x_import.xml",
        'views/x_customs_regime_views.xml',
        'views/product_template_inherit_views.xml',
        'views/choose_landed_cost_wizard_view.xml',
        'views/import_boarding_view.xml',
        'views/tariff_item_views.xml',
        'views/stock_landed_cost_taxes_view.xml',
        'views/product_pricelist_view_inherit.xml',
        'views/lc_taxes_io_wizard_views.xml',
        'views/stock_picking.xml',
        'views/stock_valuation_layer.xml',
        'views/stock_move_line.xml',
        "reports/report.xml",
        "reports/report_templates.xml",
        "views/import_report_line_views.xml",
        "views/import_report_views.xml",#View Reporte Completo Importaciones
        "data/import_report_fields.xml",#Data Reporte Completo Importaciones
        "data/import_boarding_data.xml",#Data para tabla import_boarding
    ],
    'assets': {
        'web.assets_backend': [
            'import_module/static/src/components/bank_rec_widget.js',
            'import_module/static/src/components/bank_rec_widget_view.xml',
        ],
    },
    "post_init_hook": "post_init_create_company_sequences",
    'installable': True,
    'icon': 'import_module/static/description/icon.png',
    'application': True,
    'auto_install': False,

}