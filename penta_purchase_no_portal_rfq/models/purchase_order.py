# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _name = 'purchase.order'

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        return super()._notify_get_recipients_groups(message, model_description, msg_vals=msg_vals)
