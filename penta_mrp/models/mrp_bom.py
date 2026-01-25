# -*- coding: utf-8 -*-

from odoo import models, fields, _


class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    
    unit_cost_mp = fields.Float(
        string='Cost unit - MP',
        compute='_compute_unit_cost_mp',
        help='Unit cost of materials in the BOM.'
    )
    unit_cost_mod = fields.Float(
        string='Cost unit - MOD',
        compute='_compute_unit_cost_mod',
        help='Unit cost of labor in the BOM.'
    )
    unit_cost_cif = fields.Float(
        string='Cost unit - CIF',
        compute='_compute_unit_cost_cif',
        help='Unit cost of indirect manufacturing costs in the BOM.'
    )

    def _compute_unit_cost_mp(self):
        for record in self:
            total = 0.0
            for line in record.bom_line_ids:
                total += line.total_mp_cost
            record.unit_cost_mp = total / (record.product_qty or 1.0)
            
    def _compute_unit_cost_mod(self):
        for record in self:
            total = 0.0
            for operation in record.operation_ids:
                total += operation.total_operation_cost
            record.unit_cost_mod = total / (record.product_qty or 1.0)

    def _compute_unit_cost_cif(self):
        for record in self:
            total = 0.0
            for aditional in record.mrp_bom_cost_ids:
                total += aditional.value
            record.unit_cost_cif = total / (record.product_qty or 1.0)

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
