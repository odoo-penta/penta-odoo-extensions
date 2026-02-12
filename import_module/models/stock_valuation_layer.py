# models/stock_valuation_layer.py
from odoo import models, fields

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    # Related al id_import del asiento contable
    id_import = fields.Many2one(
        'x.import',
        string='Guía de importación',
        related='stock_move_id.picking_id.id_import',
        store=True,
        index=True,
        readonly=True,
        copy=False,
    )


class StockMove(models.Model):
    _inherit = "stock.move"


    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value,
                                       debit_account_id, credit_account_id, svl_id, description):

        res = super()._generate_valuation_lines_data(
            partner_id, qty, debit_value, credit_value,
            debit_account_id, credit_account_id, svl_id, description
        )

        svl = self.env['stock.valuation.layer'].browse(svl_id)

        if svl.id_import:
            res['debit_line_vals']['id_import'] = svl.id_import.id
            res['credit_line_vals']['id_import'] = svl.id_import.id

            if 'price_diff_line_vals' in res:
                res['price_diff_line_vals']['id_import'] = svl.id_import.id

        return res

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        vals = super()._prepare_account_move_vals(
            credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost
        )

        svl = self.env['stock.valuation.layer'].browse(svl_id)

        if svl.id_import:
            vals['id_import'] = svl.id_import.id

        return vals