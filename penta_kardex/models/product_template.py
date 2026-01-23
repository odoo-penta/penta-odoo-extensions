# -*- coding: utf-8 -*-
# Part of PentaLab. See LICENSE file for full copyright and licensing details.
# © 2025 PentaLab
# License Odoo Proprietary License v1.0 (https://www.odoo.com/documentation/user/16.0/legal/licenses/licenses.html#odoo-proprietary-license)

from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_open_kardex(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'kardex.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_id': self.id},
        }

    