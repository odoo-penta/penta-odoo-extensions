from odoo import api, SUPERUSER_ID

def post_init_hook(env):
    """
    Recalculate lots and related fields in stock.valuation.layer
    when installing/updating the module.
    """

    svls = env['stock.valuation.layer'].search([])

    if not svls:
        return

    svls._compute_lot_id()


    svls._recompute_field('lot_motor_number')
    svls._recompute_field('lot_ramv')
    svls._recompute_field('lot_pdi')
