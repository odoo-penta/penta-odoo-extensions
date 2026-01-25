from odoo import models, fields, api

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    motor_number = fields.Char(
        string="Motor Number",
        related='lot_id.motor_number',
        store=True,
        readonly=True
    )

    ramv = fields.Char(
        string="RAMV",
        related='lot_id.ramv',
        store=True,
        readonly=True
    )

    def _update_motor_and_ramv(self):
        """Método reutilizable para actualizar motor_number y ramv"""
        for line in self:
            lot = line.lot_id or (line.quant_id.lot_id if line.quant_id else False)
            if lot:
                line.motor_number = lot.motor_number
                line.ramv = lot.ramv

    @api.onchange('lot_id', 'lot_name')
    def _onchange_lot_id(self):
        self._update_motor_and_ramv()

    @api.onchange('quant_id')
    def _onchange_quant_id(self):
        self._update_motor_and_ramv()

    def button_check_availability(self):
        """Ejemplo de botón que también actualiza los campos"""
        self._update_motor_and_ramv()
        return super().button_check_availability()