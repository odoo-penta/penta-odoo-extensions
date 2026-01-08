# -*- coding: utf-8 -*-

from odoo import models, fields, _


class MrpProduction(models.Model):
    _inherit = "mrp.production"
    
    def write(self, vals):
        res = super().write(vals)
        if 'product_qty' in vals:
            for prod in self:
                if prod.state in ('draft', 'confirmed'):
                    prod._recompute_workorder_durations()
        return res
    
    def _recompute_workorder_durations(self):
        for wo in self.workorder_ids:
            if wo.state not in ('draft', 'ready'):
                continue

            op = wo.operation_id
            wc = op.workcenter_id

            qty = self.product_qty
            cycle = wc.time_cycle_manual or 1

            wo.duration_expected = (
                op.time_start +
                op.time_stop +
                (qty / cycle) * op.time_cycle
            )

