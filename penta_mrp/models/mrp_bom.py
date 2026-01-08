# -*- coding: utf-8 -*-

from odoo import models,  _

class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    
    def bom_get_cost(self):
        """
        Obtiene el costo unitario de la lista de materiales (BOM).
        """
        result = {}
        for bom in self:
            total = 0.0

            # Costos de materiales
            for line in bom.bom_line_ids:
                total += line.standard_price * line.product_qty

            # Costos de operaciones
            for operation in bom.operation_ids:
                duration_expected = (
                    operation.workcenter_id._get_expected_duration(operation) +
                    (operation.time_cycle * 100 / operation.workcenter_id.time_efficiency)
                )

                cost_hour = (
                    operation.workcenter_id.costs_hour +
                    operation.workcenter_id.workcenter_team_costs_hour
                )

                total += (duration_expected / 60.0) * cost_hour

            # Costo unitario
            product_qty = bom.product_qty or 1.0
            result[bom.id] = total / product_qty

        return result
