{
    "name": "PENTA Advanced Search",
    'version': '18.0.1.0.0',
    "category": "Extra Tools",
    "summary": """Advanced search feature add field one2many_search in tree views""",
    "author": "Anthony Simbaña",
    "depends": ["web"],
    "website": "https://github.com/odoo-penta/penta-odoo-extensions",
    "assets": {
        "web.assets_backend": [
            "penta_advanced_search/static/src/css/search_bar_view.css",
            "penta_advanced_search/static/src/js/list_renderer_search_bar.js",
            "penta_advanced_search/static/src/xml/list_renderer_search_bar.xml",
        ],
    },
    "license": "AGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}
