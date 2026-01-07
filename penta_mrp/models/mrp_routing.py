# -*- coding: utf-8 -*-

from odoo import models, fields, _


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'
    
    time_cycle_minutes = fields.Integer(
        string='Time Cycle (Minutes)',
        compute='_compute_time_cycle_minutes',
        inverse='_inverse_time_cycle_minutes',
        store=True,
        default=0,
        help='Time cycle in minutes for the work center operation.'
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
