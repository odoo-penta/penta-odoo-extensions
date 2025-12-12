# -*- coding: utf-8 -*-

from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round
from odoo.tools.misc import groupby as tools_groupby
import xml.etree.ElementTree as ET
import base64


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    process_line_ids = fields.One2many('process.order.line', 'manufacture_id')
    product_is_serial = fields.Boolean(compute='_compute_product_is_serial')
    cpn_pdi_generated_at = fields.Datetime(string="CPN/PDI generated", readonly=True, copy=False)

    @api.depends('product_id')
    def _compute_product_is_serial(self):
        for rec in self:
            rec.product_is_serial = False
            if rec.product_id.tracking == 'serial' or rec.product_id.tracking == 'lot':
                rec.product_is_serial = True

    def _set_qty_producing(self, pick_manual_consumption_moves=True):
        if self.product_is_serial:
            return True
        else:
            return super(MrpProduction, self)._set_qty_producing(pick_manual_consumption_moves)

    def action_button_done(self):
        moves_to_do, moves_not_to_do = set(), set()
        for move in self.move_raw_ids:
            if move.state == 'done':
                moves_not_to_do.add(move.id)
            elif move.state != 'cancel':
                moves_to_do.add(move.id)
                qty_done = sum(move.move_line_ids.mapped('qty_done'))
                if move.product_qty == 0.0 and qty_done > 0:
                    move.product_uom_qty = qty_done
        self.env['stock.move'].browse(moves_to_do)._action_done(cancel_backorder=False)
        moves_to_do = self.move_raw_ids.filtered(lambda x: x.state == 'done') - self.env['stock.move'].browse(moves_not_to_do)
        # Create a dict to avoid calling filtered inside for loops.
        moves_to_do_by_order = defaultdict(lambda: self.env['stock.move'], [
            (key, self.env['stock.move'].concat(*values))
            for key, values in tools_groupby(moves_to_do, key=lambda m: m.raw_material_production_id.id)
        ])
        for order in self:
            finish_moves = order.move_finished_ids.filtered(lambda m: m.product_id == order.product_id and m.state not in ('done', 'cancel'))
            qty_done_finish = sum(finish_moves.move_line_ids.mapped('qty_done'))
            # the finish move can already be completed by the workorder.
            if finish_moves and qty_done_finish == 0:
                finish_moves._set_quantity_done(float_round(order.qty_producing - order.qty_produced, precision_rounding=order.product_uom_id.rounding, rounding_method='HALF-UP'))
                finish_moves.move_line_ids.lot_id = order.lot_producing_id
            order._cal_price(moves_to_do_by_order[order.id])
        moves_to_finish = self.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
        moves_to_finish = moves_to_finish._action_done(cancel_backorder=False)
        self.action_assign()
        (self.move_raw_ids | self.move_finished_ids).filtered(lambda x: x.state not in ('done', 'cancel')).write({
            'state': 'done',
            'product_uom_qty': 0.0,
        })
        for production in self:
            production.write({
                'date_finished': fields.Datetime.now(),
                'product_qty': production.qty_producing or production.product_qty,
                'priority': '0',
                'is_locked': True,
                'state': 'done',
            })
        return True
    
    def _finished_move_lines_to_process(self):
        self.ensure_one()
        moves = self.move_finished_ids
        lines = moves.mapped("move_line_ids").filtered(
            lambda ml: ml.product_id and ml.product_id.tracking != "none"
        )
        return lines

    def action_open_generate_cpn_pdi_wizard(self):
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_("The order must be in the following status: Done"))
        return {
            "type": "ir.actions.act_window",
            "res_model": "generate.cpn.pdi.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_production_id": self.id},
        }

    def action_generate_xml(self):
        for prod in self:
            if prod.state != "done":
                raise UserError(_("The order must be in 'Done' state to generate the XML."))

            root = ET.Element("vehiculosEnsambladores")
            for ml in prod._finished_move_lines_to_process():
                lot = ml.lot_id
                if not lot:
                    continue
                veh = ET.SubElement(root, "vehiculoEnsamblador")
                ET.SubElement(veh, "numeroProduccion").text = prod.name or ""
                ET.SubElement(veh, "producto").text = ml.product_id.display_name or ""
                ET.SubElement(veh, "lotSerial").text = lot.name or ""
                ET.SubElement(veh, "cpn").text = lot.cpn or ""
                ET.SubElement(veh, "pdi").text = lot.pdi or ""
                subclass = prod.product_id.product_tmpl_id.sri_motor_subclass_id
                if subclass:
                    sri = ET.SubElement(veh, "sri")
                    ET.SubElement(sri, "codigoSubclaseSubcategoria").text = subclass.subclass_subcategory_code or ""
                    ET.SubElement(sri, "codigoSubclase").text = subclass.subclass_code or ""
                    ET.SubElement(sri, "idSRI").text = subclass.sri_id or ""

            data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            att = self.env["ir.attachment"].create({
                "name": f"produccion_{prod.name}.xml",
                "res_model": "mrp.production",
                "res_id": prod.id,
                "type": "binary",
                "datas": base64.b64encode(data).decode(),
                "mimetype": "application/xml",
            })

            prod.message_post(
                body=_("The XML file was generated and attached to the record."),
                attachment_ids=[att.id],
            )
        return True
    
    def action_auto_produce(self):
        for production in self:
            product = production.product_id
            total_qty = production.product_qty # Cantidad total planificada
            produced_qty = production.qty_producing # Cantidad ya producida
            pending_qty = total_qty - produced_qty
            
            if total_qty <= 0:
                raise ValidationError(_(
                    "It cannot be produced because the total quantity set is zero or negative."
                ))
                
            if pending_qty <= 0:
                raise ValidationError(_(
                    "The order has already been fully produced. There are no units left."
                ))
                
            # CANTIDAD A PRODUCIR EN ESTA EJECUCIÓN
            if product.tracking == 'serial':
                qty_to_make = 1
            else:
                qty_to_make = pending_qty  # produce toda la pendiente
            
            # 1) Validación de serial si aplica
            if product.tracking == 'serial':
                lot = self.env['stock.lot'].create({
                    'product_id': product.id,
                    'company_id': production.company_id.id,
                    'name': self.env['stock.lot']._get_next_serial(production.company_id, product)
                        or self.env['ir.sequence'].next_by_code('stock.lot.serial'),
                })
            else:
                lot = False

            # 2) Move finished
            for move in production.move_finished_ids.filtered(lambda m: m.product_id == product):
                existing_ml = move.move_line_ids.filtered(
                    lambda ml: not ml.lot_id and ml.qty_done == 0
                )
                if existing_ml:
                    move_line_id = existing_ml[0]
                else:
                    vals = move._prepare_move_line_vals(quantity=0)
                    move_line_id = self.env['stock.move.line'].create(vals)

                move_line_id.write({
                    'qty_done': qty_to_make,
                    'product_uom_id': product.uom_id.id,
                    'lot_id': lot.id if lot else False,
                    'production_id': production.id,
                })

            # 3) Consumir materia prima automáticamente
            for raw_move in production.move_raw_ids:
                consumed = sum(raw_move.move_line_ids.mapped("qty_done"))
                pending_raw = raw_move.product_uom_qty - consumed
                if pending_raw <= 0:
                    continue

                ml_vals = raw_move._prepare_move_line_vals(quantity=0)
                ml_vals.update({
                    'qty_done': pending_raw,
                    'product_uom_id': raw_move.product_id.uom_id.id,
                    'lot_id': False,
                    'production_id': production.id,
                })
                self.env['stock.move.line'].create(ml_vals)

            # 4) Actualizar cantidad producida
            production.qty_producing += qty_to_make

            # 5) Cerrar si está totalmente producida
            if production.qty_producing >= production.product_qty:
                production.state = 'to_close'

        return True


class StockLot(models.Model):
    _inherit = 'stock.lot'

    attachment_ids = fields.Many2many('ir.attachment')
