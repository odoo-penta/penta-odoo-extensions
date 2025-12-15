# -*- coding: utf-8 -*-

from odoo import models, fields, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    active_financing = fields.Boolean(string='Active Financing', default=False)
    factor_to_apply = fields.Float(string='Entry amount', readonly=True)
    entry_percentage = fields.Float(string='Entry (%)', default=0, readonly=True)
    risk_percentage = fields.Float(string='Risk (%)', default=0, readonly=True)
    interest = fields.Float(string='Interest (%)', default=0, readonly=True)
    month_interest = fields.Float(string='Monthly Interest (%)', readonly=True)
    months_of_grace = fields.Integer(string='Months of Grace', default=0, readonly=True)
    apply_interest_grace = fields.Boolean(string='Apply Interest Grace', default=False, readonly=True)
    proration = fields.Boolean(string='Proration', default=False, readonly=True)
    minimum_fee = fields.Monetary(string='Minimum Fee', default=0.0, readonly=True)
    payment_period = fields.Integer(readonly=True)
    financing_amount = fields.Monetary(string='Financing Amount', readonly=True)
    total_interest_amount = fields.Monetary(string='Total Interest Amount', readonly=True)
    line_deferred_ids = fields.One2many('account.move.line.deferred', 'move_id', string='Deferred Lines', readonly=True)
    
class AccountMoveLineDeferred(models.Model):
    _name = 'account.move.line.deferred'
    _description = 'Move Line Deferred'
    
    move_id = fields.Many2one('account.move', string='Account Move')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='move_id.currency_id',
        store=True,
        readonly=True
    )
    month = fields.Integer(string='Month')
    initial_balance = fields.Monetary(string='Initial Balance', currency_field='currency_id')
    interest_amount = fields.Monetary(string='Interest Amount', currency_field='currency_id')
    amortization = fields.Monetary(string='Amortization', currency_field='currency_id')
    additional_grace_interest = fields.Monetary(string='Additional Grace Interest', currency_field='currency_id')
    final_balance = fields.Monetary(string='Final Balance', currency_field='currency_id')
    fixed_fee = fields.Float(string='Fixed fee', currency_field='currency_id')
    due_date = fields.Date(string='Due Date')