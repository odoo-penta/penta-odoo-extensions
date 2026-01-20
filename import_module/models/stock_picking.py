from odoo import models, api, fields

class stock_picking_module(models.Model):
    _inherit = 'stock.picking'
    
    id_import = fields.Many2one(
        'x.import',
        string='Guía de importación',
        index=True,
        copy=False,
    )

    # Reemplaza _get_import_from_origin para usar el campo nativo
    def _get_import_from_origin(self):
        """Devuelve id_import (ID) usando únicamente el 'origin' como nombre exacto de la PO."""
        self.ensure_one()
        if (self.picking_type_code or '') != 'incoming' or not self.origin:
            return False

        po = self.env['purchase.order'].search([
            ('name', '=', self.origin),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        return po.id_import.id if po and po.id_import else False


    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking in pickings:
            # Asignar id_import desde la PO (origin) solo en recepciones
            if (picking.picking_type_id.code or '') == 'incoming' and not picking.id_import:
                imp_id = picking._get_import_from_origin()
                if imp_id:
                    picking.sudo().write({'id_import': imp_id})

            # Si ya viene con date_done, actualiza la fecha en la importación
            if picking.date_done:
                picking.update_purchase_order_date()
        return pickings

    def action_backfill_import_on_receipts(self):
        """Rellena id_import en recepciones existentes (solo usando origin -> PO)."""
        receipts = self.search([
            ('picking_type_code', '=', 'incoming'),
            ('id_import', '=', False),
        ])
        for picking in receipts:
            imp_id = picking._get_import_from_origin()
            if imp_id:
                picking.sudo().write({'id_import': imp_id})
                    

    # Mantén write SOLO para reaccionar a cambios de date_done
    def write(self, vals):
        res = super().write(vals)
        if vals.get('date_done'):
            self.update_purchase_order_date()
        return res


    def update_purchase_order_date(self):
        for picking in self:
            purchase_orders = picking.move_ids.mapped('purchase_line_id.order_id')
            for po in purchase_orders:
                for x_import in po.id_import:
                    if picking.date_done and not x_import.date_entry_into_inventory:
                        x_import.date_entry_into_inventory = picking.date_done
                        break  # Salir del bucle una vez que se ha encontrado la primera fecha
