# -*- coding: utf-8 -*-

from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )

        if not self:
            return groups

        self.ensure_one()

        # Quitar botón SOLO en cotizaciones (RFQ)
        if self.state in ('draft', 'sent'):
            for group in groups:
                if group[0] == 'portal_customer':
                    group[2].pop('button_access', None)
                    group[2].pop('actions', None)

        return groups
