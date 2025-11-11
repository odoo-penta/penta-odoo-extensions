from odoo import models, fields, api

class AccountMoveStock(models.Model):
    _inherit = 'account.move'

    stock_lot_ids = fields.One2many(
        'stock.lot',
        compute='_compute_stock_lot_ids',
        string="Lotes Relacionados",
        store=False
    )

    @api.depends('invoice_line_ids')
    def _compute_stock_lot_ids(self):
        """Obtiene todos los lotes relacionados con las líneas de la factura."""
        for move in self:
            lots = self.env['stock.lot']
            # Recorremos cada línea de factura
            for line in move.invoice_line_ids:
                # Verificamos si la línea tiene un producto
                if line.product_id:
                    # Buscamos los movimientos de stock vinculados al producto y al origen de la factura
                    stock_moves = self.env['stock.move'].search([
                        ('product_id', '=', line.product_id.id),
                        ('picking_id.origin', '=', move.invoice_origin),
                        ('state', '=', 'done'),
                    ])
                    # De los stock.moves, tomamos los lotes usados en stock.move.line
                    move_lines = self.env['stock.move.line'].search([
                        ('move_id', 'in', stock_moves.ids),
                        ('lot_id', '!=', False)
                    ])
                    lots |= move_lines.mapped('lot_id')
            move.stock_lot_ids = lots
