from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import requests
from urllib.parse import urlencode
import unicodedata

SRI_BASE = "https://srienlinea.sri.gob.ec/sri-catastro-sujeto-servicio-internet/rest/Persona/obtenerPorTipoIdentificacion"


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --------------------------
    # Utils
    # --------------------------
    @staticmethod
    def _vat_digits(v):
        return ''.join(ch for ch in (v or '') if ch.isdigit())

    @staticmethod
    def _ident_type_ec(digits):
        return 'C' if len(digits) == 10 else ('R' if len(digits) == 13 else None)

    @staticmethod
    def _normalize_name(txt):
        if not txt:
            return ''
        nfkd = unicodedata.normalize('NFKD', txt)
        no_accents = ''.join(c for c in nfkd if not unicodedata.combining(c))
        return ' '.join(no_accents.strip().split()).upper()

    def _sri_lookup(self, digits, tipo):
        """Consulta al SRI y retorna (ok, data, mensaje)."""
        try:
            url = f"{SRI_BASE}?{urlencode({'numeroIdentificacion': digits, 'tipoIdentificacion': tipo})}"
            resp = requests.get(url, headers={"Content-Type": "application/json"}, timeout=5)

            if resp.status_code != 200:
                return False, {}, _("SRI no responde correctamente.")

            data = resp.json() if (resp.text or '').strip() else {}

            ident = data.get('identificacion')
            nombre = data.get('nombreCompleto')

            if not ident or not nombre:
                return False, data, _("Identificación no encontrada en SRI.")

            if str(ident).strip() != digits:
                return False, data, _("Respuesta SRI inconsistente.")

            return True, data, _("Identificación válida según SRI.")

        except requests.Timeout:
            return False, {}, _("Tiempo de espera agotado al consultar SRI.")
        except Exception as e:
            return False, {}, _("Error consultando SRI: %s") % (str(e) or repr(e))

    # --------------------------
    # Onchange VAT Ecuador
    # --------------------------
    @api.onchange('vat')
    def _onchange_vat_ec_online(self):
        for rec in self:

            if not rec.vat:
                continue

            # Solo dígitos
            digits = self._vat_digits(rec.vat)
            rec.vat = digits

            # Tipo C o R
            tipo = self._ident_type_ec(digits)
            if not tipo:
                return  # longitud inválida

            # Solo para Ecuador
            if rec.country_id and rec.country_id.code != 'EC':
                return

            # Consulta al SRI
            ok, data, msg = rec._sri_lookup(digits, tipo)

            if not ok:
                # No llenamos ni alertamos, solo no hacemos nada
                return

            # --------------------------
            # Autocompletar nombre
            # --------------------------
            sri_name = (data.get('nombreCompleto') or '').strip().upper()

            if not rec.name:
                rec.name = sri_name
            else:
                # Si el usuario ya puso un nombre distinto, lanzar warning
                norm_user = self._normalize_name(rec.name)
                norm_sri = self._normalize_name(sri_name)

                if norm_user != norm_sri:
                    return {
                        'warning': {
                            'title': _("Nombre diferente al SRI"),
                            'message': _("El nombre ingresado no coincide con el registrado en el SRI:\n\nSRI: %s") % sri_name,
                        }
                    }

        return
