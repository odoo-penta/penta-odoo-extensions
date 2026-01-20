from odoo import models, fields, _ 

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    landed_cost_type = fields.Selection([
        ('freight', 'Costo de flete'),
        ('insurance', 'Costo de seguro'),
        ('customs', 'Costo de aduana'),
    ], string="Tipo de Costo", help="Indica el tipo de costo de importación que representa este producto.")

    sri_subcategory = fields.Selection(
        selection=[
            ('na', 'N/A'),
            ('ok', 'OK')
        ],
        string="Subcategoría SRI",
        default='na'
    )
    
    tariff_item_id = fields.Many2one('tariff.item', string='Partida Arancelaria')

    type_classification = fields.Selection(
        selection=[
            ("ad_valorem", "Ad Valorem"),
            ("fodinfa", "Fodinfa"),
            ("ice", "ICE"),
            ("recargo_ice", "Recargo ICE"),
        ],
        string="Clasificación (Aranceles)",
        help=_("Clasificación arancelaria usada para reportes de importaciones."),
    )

    import_iva_flag = fields.Boolean(
        string="Tomar para IVA (reporte importaciones)",
        help=_("Si está activo, las líneas de factura de este producto aportan el monto de impuestos (tax_ids) al campo IVA del reporte de importaciones."),
    )
