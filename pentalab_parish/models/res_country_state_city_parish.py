# models/res_country_state_city_parish.py
from odoo import models, fields, api, _
import re
import os, csv, logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def _last2(s: str) -> str:
    s = (s or '').strip()
    # toma solo dígitos por si vinieran guiones/espacios
    digits = ''.join(ch for ch in s if ch.isdigit())
    return digits[-2:] if len(digits) >= 2 else digits.zfill(2)

def _only_digits(s: str) -> str:
    return ''.join(ch for ch in (s or '') if ch.isdigit())

class ResCountryStateCityParish(models.Model):
    _name = 'res.country.state.city.parish'
    _description = 'Parroquias'

    name = fields.Char(required=True, index=True)
    code = fields.Char(string="Código (2 dígitos)", required=True, index=True)  # <- 2 dígitos finales de la parroquia
    city_id = fields.Many2one('res.country.state.city', string="Ciudad/Cantón", required=True, index=True)

    _sql_constraints = [
        ('uniq_parish_code_per_city',
         'unique(code, city_id)',
         'El código de parroquia debe ser único dentro de la ciudad.'),
    ]

    @api.constrains('code')
    def _check_code_len(self):
        for rec in self:
            if not rec.code or not re.fullmatch(r'\d{2}', rec.code):
                raise ValueError("El código de parroquia debe tener exactamente 2 dígitos.")
    def _capitalize_name(self, text):
        """
        Convierte el texto a formato: Primera Letra Mayúscula.
        Soporta tildes, ñ, y múltiples palabras.
        Ej: 'SAN BLAS' -> 'San Blas', 'CHECA (JIDCAY)' -> 'Checa (Jidcay)'
        """
        if not text:
            return ''
        text = text.strip().lower()
        # Capitalizar cada palabra, respetando espacios y paréntesis
        def cap(match):
            return match.group(0).capitalize()
        text = re.sub(r'(\b\w+)', cap, text)
        return text
    
    def _load_ec_divisions_from_csv(self, strict=True):
        """
        CSV: province_code,province_name,canton_code,canton_name,parish_code,parish_name
        - UPSERT: provincias, ciudades, parroquias
        - codes de ciudad/parroquia: últimos 2 dígitos
        - strict=True: cualquier error -> rollback total
        """
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(module_path, 'data', 'ec_divisions_parishes.csv')

        country = self.env['res.country'].search([('name', '=', 'Ecuador')], limit=1)
        if not country:
            raise UserError("No existe el país 'Ecuador'. Cree el país antes de importar.")

        created_states = updated_states = 0
        created_cities = updated_cities = 0
        created_parishes = updated_parishes = 0

        try:
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)

                raw_headers = reader.fieldnames or []

                def _norm(h: str) -> str:
                    return (h or '').replace('\ufeff', '').strip().lower()

                header_map = { _norm(h): h for h in raw_headers }
                required = {'province_code','province_name','canton_code','canton_name','parish_code','parish_name'}
                if not required.issubset(set(header_map.keys())):
                    raise UserError(
                        "El CSV debe contener las columnas: "
                        + ", ".join(sorted(required))
                        + f". Encabezados leídos: {raw_headers}"
                    )

                def val(row, key):
                    return (row.get(header_map[key]) or '').strip()

                for i, row in enumerate(reader, start=2):
                    p_code_full = _only_digits(val(row, 'province_code'))
                    c_code_full = _only_digits(val(row, 'canton_code'))
                    pa_code_full = _only_digits(val(row, 'parish_code'))

                    p_name_raw  = val(row, 'province_name')
                    c_name_raw  = val(row, 'canton_name')
                    pa_name_raw = val(row, 'parish_name')

                    # 2) Normaliza capitalización (Primera Letra Mayúscula)
                    p_name  = self._capitalize_name(p_name_raw)
                    c_name  = self._capitalize_name(c_name_raw)
                    pa_name = self._capitalize_name(pa_name_raw)

                    if not (p_code_full and p_name and c_code_full and c_name and pa_code_full and pa_name):
                        msg = f"Fila {i}: datos incompletos: {row}"
                        if strict: raise UserError(msg)
                        _logger.warning(msg); continue

                    state_code_2  = _last2(p_code_full)
                    city_code_2   = _last2(c_code_full)
                    parish_code_2 = _last2(pa_code_full)

                    # ---------- PROVINCIA (UPSERT) ----------
                    state = self.env['res.country.state'].search([
                        ('country_id', '=', country.id),
                        ('code', '=', state_code_2),
                    ], limit=1)

                    if not state:
                        # fallback por nombre (tolerante a tildes/casing)
                        state = self.env['res.country.state'].search([
                            ('country_id', '=', country.id),
                            ('name', 'ilike', p_name),
                        ], limit=1)

                    if state:
                        vals_state = {}
                        if state.name != p_name:
                            vals_state['name'] = p_name
                        if not state.code or _only_digits(state.code) != state_code_2:
                            # normaliza a 2 dígitos (evita '1' vs '01')
                            vals_state['code'] = state_code_2
                        if vals_state:
                            state.write(vals_state)
                            updated_states += 1
                    else:
                        # Crear si no existía (ahora sí permitido)
                        state = self.env['res.country.state'].create({
                            'name': p_name,
                            'code': state_code_2,
                            'country_id': country.id,
                        })
                        created_states += 1

                    # ---------- CIUDAD / CANTÓN (UPSERT) ----------
                    city = self.env['res.country.state.city'].search([
                        ('code', '=', city_code_2),
                        ('state_id', '=', state.id)
                    ], limit=1)

                    vals_city = {
                        'name': c_name,
                        'code': city_code_2,
                        'state_id': state.id,
                        'country_id': country.id,
                    }

                    if city:
                        city.write(vals_city); updated_cities += 1
                    else:
                        city = self.env['res.country.state.city'].create(vals_city); created_cities += 1

                    if not city:
                        msg = f"Fila {i}: no se pudo crear/localizar la ciudad '{c_name}' (provincia {p_name})."
                        if strict: raise UserError(msg)
                        _logger.error(msg); continue

                    # ---------- PARROQUIA (UPSERT) ----------
                    parish = self.search([
                        ('code', '=', parish_code_2),
                        ('city_id', '=', city.id)
                    ], limit=1)

                    vals_parish = {
                        'name': pa_name,
                        'code': parish_code_2,
                        'city_id': city.id,
                    }

                    if parish:
                        parish.write(vals_parish); updated_parishes += 1
                    else:
                        self.create(vals_parish); created_parishes += 1

            _logger.info(
                "Importación OK. Provincias +%s(↑%s), Ciudades +%s(↑%s), Parroquias +%s(↑%s)",
                created_states, updated_states, created_cities, updated_cities,
                created_parishes, updated_parishes
            )
            return True

        except Exception as e:
            _logger.error("Error en importación: %s", e)
            self.env.cr.rollback()
            raise