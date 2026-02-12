from odoo import fields, models


class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    viaticos_city_origin_policy = fields.Selection(
        [
            ("no", "Ninguno"),
            ("optional", "Opcional"),
            ("required", "Requerido"),
        ],
        string="Ciudad origen",
        default="no",
        required=True,
    )

    viaticos_city_destination_policy = fields.Selection(
        [
            ("no", "Ninguno"),
            ("optional", "Opcional"),
            ("required", "Requerido"),
        ],
        string="Ciudad destino",
        default="no",
        required=True,
    )

    viaticos_control = fields.Boolean(
        string="Activar control de viaticos",
        help="Si esta activo, la solicitud mostrara campos y validaciones especificas de viaticos.",
    )

    viaticos_date_from_allowed = fields.Date(
        string="Fecha desde permitido",
        help="Desde que fecha (hoy) se permite solicitar viaticos.",
    )

    viaticos_date_to_allowed = fields.Date(
        string="Fecha hasta permitido",
        help="Hasta que fecha (hoy) se permite solicitar viaticos.",
    )
