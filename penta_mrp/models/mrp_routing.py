# -*- coding: utf-8 -*-

from odoo import api, models, fields, _


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'
    
    time_cycle_minutes = fields.Integer(
        string='Time Cycle',
        compute='_compute_time_cycle_minutes',
        inverse='_inverse_time_cycle_minutes',
        store=True,
        default=0,
        help='Time cycle in minutes for the work center operation.'
    )
    workcenter_team_costs_hour = fields.Float(
        related='workcenter_id.workcenter_team_costs_hour',
        depends=['workcenter_id'],
        readonly=True,
    )
    total_operation_cost = fields.Float(
        string='Total Operation Cost',
        compute='_compute_total_operation_cost',
        store=True,
        help='Total cost based on workcenter hourly cost and time cycle.'
    )
    
    @api.depends('time_cycle', 'workcenter_team_costs_hour')
    def _compute_total_operation_cost(self):
        for record in self:
            record.total_operation_cost = (
                record.workcenter_team_costs_hour * record.time_cycle
            )
    
    @api.depends('time_cycle_manual')
    def _compute_time_cycle_minutes(self):
        for record in self:
            if record.time_cycle_manual:
                # time_cycle_manual está en HORAS (float)
                record.time_cycle_minutes = int(round(record.time_cycle_manual * 60))
            else:
                record.time_cycle_minutes = 0

    def _inverse_time_cycle_minutes(self):
        for record in self:
            if record.time_cycle_minutes:
                # convertir minutos enteros a horas (float)
                record.time_cycle_manual = record.time_cycle_minutes / 60.0
            else:
                record.time_cycle_manual = 0.0
