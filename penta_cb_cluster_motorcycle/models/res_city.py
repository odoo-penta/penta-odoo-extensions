from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResCity(models.Model):
    _inherit = 'res.city'

    l10n_ec_penta_code_city = fields.Char(
        string='EC City Code',
        compute='_compute_l10n_ec_penta_code_city',
        store=True,
        help='Código de la ciudad según el SRI (Ecuador).',
    )

    @api.depends('name', 'state_id', 'state_id.l10n_ec_penta_code_state')
    def _compute_l10n_ec_penta_code_city(self):
        # Detecta si existe el modelo alterno
        alt_model_name = 'res.country.state.city'   # tu modelo alterno
        alt_model_exists = alt_model_name in self.env

        for rec in self:
            # 1) Prefijo de provincia (tu campo propio en state)
            pref = (rec.state_id and rec.state_id.l10n_ec_penta_code_state) or False
            if not pref:
                rec.l10n_ec_penta_code_city = False
                continue

            # 2) Código de ciudad (dos rutas posibles)
            city_code = None

            # 2.a) Si la localización del partner añadió l10n_ec_code en res.city, úsalo
            #     (getattr evita reventar si el campo no existe)
            raw = getattr(rec, 'l10n_ec_code', None)
            if raw:
                city_code = str(raw).zfill(2)  # normaliza a 2 dígitos

            # 2.b) Si no existe ese campo, intenta resolver con tu modelo alterno
            if not city_code and alt_model_exists:
                Alt = self.env[alt_model_name]
                # Ajusta estos criterios a tu esquema (por ejemplo, empatar por ciudad+estado)
                alt = Alt.search([
                    ('name', '=', rec.name),
                    ('state_id', '=', rec.state_id.id),
                ], limit=1)
                if alt:
                    # Elige el campo real de tu modelo alterno:
                    # intenta 'l10n_ec_code' y si no, 'code'
                    alt_code = getattr(alt, 'l10n_ec_code', None) or getattr(alt, 'code', None)
                    if alt_code:
                        city_code = str(alt_code).zfill(2)

            # 3) Arma el código final o deja False si no se pudo inferir
            rec.l10n_ec_penta_code_city = f"{pref}{city_code}" if (pref and city_code) else False