from . import models

def _main_load_cities_from_csv(env):
    # Nuevo: un solo loader jerárquico
    env['res.country.state.city.parish']._load_ec_divisions_from_csv()
    env['res.country.state.region']._load_ec_divisions_region_from_csv()