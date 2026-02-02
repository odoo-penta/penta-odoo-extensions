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
        # Obtener tiempo real por unidad de cada operacion de la lista de materiales
        bom = self.bom_id
        bom_product_qty = bom.product_qty
        operations = {}
        
        for operation in bom.operation_ids:
            operations[operation.id] = operation.time_cycle_manual / bom_product_qty
        
        for wo in self.workorder_ids:
            if wo.state not in ('pending', 'ready', 'waiting'):
                continue

            op = wo.operation_id
            
            if op.id not in operations:
                continue

            wo.duration_expected = operations[op.id] * self.product_qty
            
    def open_journal_items_view(self):
        self.ensure_one()
        return {
            'name': _('Journal Items'),
            'view_mode': 'list',
            'res_model': 'account.move.line',
            'views': [(False, 'list')],
            'type': 'ir.actions.act_window',
            'domain': [
                '|',
                ('move_id.name', 'ilike', self.name),
                ('move_id.ref', 'ilike', self.name),
            ],
        }
