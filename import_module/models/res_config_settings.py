from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    penta_skip_import_check_landed_cost = fields.Boolean(
        string="Permitir costos en destino sin Importación",
        config_parameter="penta.skip_import_check_landed_cost",
        help="Si está activo, permite crear Costos en destino desde factura aunque no tenga Importación asociada.",
        default = True,
    )
