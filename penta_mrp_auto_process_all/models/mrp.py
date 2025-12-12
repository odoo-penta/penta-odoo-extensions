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
    cpn_pdi_generated_at = fields.Datetime(string="CPN/PDI generados", readonly=True, copy=False)

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
        if self.state not in ("confirmed", "progress"):
            raise UserError(_("La orden debe estar en estado 'Listo' o 'En Progreso'."))
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
                raise UserError(_("La orden debe estar en estado 'Hecho' para generar el XML."))

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
                body=_("Se generó el XML y se adjuntó al registro."),
                attachment_ids=[att.id],
            )
        return True


class StockLot(models.Model):
    _inherit = 'stock.lot'

    attachment_ids = fields.Many2many('ir.attachment')
