{
    'name': 'Partner Parroquias',
    'version': '1.0',
    'category': 'Contacts',
    'summary': 'Agrega un campo de parroquias en los contactos',
    'author': 'Penta',
    'depends': ['base', 'contacts','account'],
    'data': [
        'views/res_partner_views.xml',
        'views/res_country_state_city.xml',
        'views/res_country_state_city_parroquia_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'post_init_hook': '_main_load_cities_from_csv',
}
