# -*- coding: utf-8 -*-

from odoo import models,  _


class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    
    def bom_get_cost(self):
        """
        Obtiene el costo unitario de la lista de materiales (BOM).
        """
        self.ensure_one()
        total = 0.0
        

        # Costos de materiales
        for line in self.bom_line_ids:
            total += line.standard_price * line.product_qty

        # Costos de operaciones
        for operation in self.operation_ids:
            workcenter = operation.workcenter_id
            time_cycle_hours = operation.time_cycle or 0.0
            efficiency = workcenter.time_efficiency or 100.0
            
            duration_expected = (time_cycle_hours * 60.0) / (efficiency / 100)

            cost_hour = (
                workcenter.costs_hour +
                workcenter.workcenter_team_costs_hour
            )

            total += (duration_expected / 60.0) * cost_hour

        # Costo unitario
        return total / (self.product_qty or 1.0)
