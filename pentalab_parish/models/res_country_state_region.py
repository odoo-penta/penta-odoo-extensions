# models/res_country_state_region.py
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

class ResCountryStateRegion(models.Model):
    _name = 'res.country.state.region'
    _description = 'Regiones (Provincias)'

    name = fields.Char(required=True, index=True)

    code = fields.Char(string="Código (2 dígitos)", required=False, index=True)

    state_id = fields.Many2one(
        "res.country.state", 
        string="Provincia", 
    ) 
    
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

    def _load_ec_divisions_region_from_csv(self, strict=True):
        """
        CSV: province_code,province_name,canton_code,canton_name,parish_code,parish_name
        - UPSERT: provincias, ciudades, parroquias
        - codes de ciudad/parroquia: últimos 2 dígitos
        - strict=True: cualquier error -> rollback total
        """
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(module_path, 'data', 'ec_divisiones_region.csv')

        country = self.env['res.country'].search([('name', '=', 'Ecuador')], limit=1)
        if not country:
            raise UserError("No existe el país 'Ecuador'. Cree el país antes de importar.")

        created_states = updated_states = 0
        created_regions = updated_regions = 0

        try:
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)

                raw_headers = reader.fieldnames or []

                def _norm(h: str) -> str:
                    return (h or '').replace('\ufeff', '').strip().lower()

                header_map = { _norm(h): h for h in raw_headers }
                required = {'province_code','province_name','region_code','region_name'}
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
                    re_code_full = _only_digits(val(row, 'region_code'))

                    p_name_raw  = val(row, 'province_name')
                    re_name_raw = val(row, 'region_name')

                    # 2) Normaliza capitalización (Primera Letra Mayúscula)
                    p_name  = self._capitalize_name(p_name_raw)
                    re_name = self._capitalize_name(re_name_raw)

                    if not (p_code_full and p_name and re_code_full and re_name):
                        msg = f"Fila {i}: datos incompletos: {row}"
                        if strict: raise UserError(msg)
                        _logger.warning(msg); continue

                    state_code_2  = _last2(p_code_full)
                    region_code_2 = _last2(re_code_full)

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

                    # ---------- REGION (UPSERT) ----------
                    region = self.search([
                        ('code', '=', region_code_2),
                        ('state_id', '=', state.id)
                    ], limit=1)

                    vals_region = {
                        'name': re_name,
                        'code': region_code_2,
                        'state_id': state.id,
                    }

                    if region:
                        region.write(vals_region); updated_regions += 1
                    else:
                        self.create(vals_region); created_regions += 1

            _logger.info(
                "Importación OK. Regiones +%s(↑%s)",
                created_regions, updated_regions
            )
            return True

        except Exception as e:
            _logger.error("Error en importación: %s", e)
            self.env.cr.rollback()
            raise