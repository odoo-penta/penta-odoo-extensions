from odoo import api, fields, models
from odoo.osv import expression
import ast


class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    partner_ids = fields.Many2many(
        'res.partner',
        string='Specific Customers',
        domain=[('is_customer', '=', True)],
        help='Apply the rule only to these customers.'
    )
    partner_category_ids = fields.Many2many(
        'res.partner.category',
        string='Customer Tags',
        help='Rule only applies to customers having at least one of these tags.'
    )
    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string='Allowed Warehouses',
        help='Rule only applies if the sale order is created in one of these warehouses.'
    )
    
    def _is_order_eligible(self, order):
        self.ensure_one()
        # Cliente específico
        if self.partner_ids and order.partner_id not in self.partner_ids:
            return False
        # Etiquetas del cliente
        if self.partner_category_ids:
            if not (order.partner_id.category_id & self.partner_category_ids):
                return False
        # Bodega
        if self.warehouse_ids:
            if order.warehouse_id not in self.warehouse_ids:
                return False
        return True
