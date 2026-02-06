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

            color = ""
            root = ET.Element("vehiculosEnsambladores")
            cabecera = ET.SubElement(root, "cabeceraEnsambladores")
            ET.SubElement(cabecera, "rucEnsambladores").text = self.env.company.vat or ""
            subclass = self.env["sri.motor.subclass"].search([("product_tmpl_id", "=", prod.product_tmpl_id.id)])
            if not subclass:
                raise UserError(_("No hay subcategoria subclase de la moto para generar el XML."))
            product_atributes = prod.product_id.attribute_line_ids

            for attr in product_atributes:
                if attr.attribute_id.name.lower() == "color":
                    color = attr.value_ids[0].name

            for ml in prod._finished_move_lines_to_process():
                lot = ml.lot_id
                if not lot:
                    continue
                veh = ET.SubElement(root, "datosVehiculosEnsambladores")
                ET.SubElement(veh, "CPN").text = lot.cpn or ""
                ET.SubElement(veh, "serialVIN").text = lot.name or ""
                ET.SubElement(veh, "fechaEmisionCPN").text = prod.cpn_pdi_generated_at.strftime("%d-%m-%Y") if prod.cpn_pdi_generated_at else ""
                ET.SubElement(veh, "codigoSubCategoriaSubClase").text = subclass.subclass_subcategory_code or ""
                ET.SubElement(veh, "numeroMotor").text = lot.motor_number or ""
                ET.SubElement(veh, "cilindraje").text = subclass.cylinder_value_id.name or ""
                ET.SubElement(veh, "tipoCombustible").text = subclass.fuel_value_id.name or ""
                ET.SubElement(veh, "tipoCarroceria").text = subclass.bodywork_value_id.name or ""
                ET.SubElement(veh, "capacidadPasajeros").text = subclass.capacity_value_id.name or ""
                ET.SubElement(veh, "numeroCKD").text = lot.cpn or ""
                ET.SubElement(veh, "cargaUtil").text = subclass.weight_value_id.name or ""
                ET.SubElement(veh, "precioVentaDealer").text = str(subclass.sri_value) or ""
                ET.SubElement(veh, "color1").text = color or ""

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
            qty_to_produce = int(production.product_qty - production.qty_producing)

            if qty_to_produce <= 0:
                raise UserError(_("The production order is already completed."))

            # ==============================
            # 1) OBTENER CKD (materia prima serializada)
            # ==============================
            ckd_moves = production.move_raw_ids.filtered(
                lambda m: m.product_id.tracking == 'serial'
            )

            if not ckd_moves:
                raise UserError(_("No CKD serial-tracked raw material found."))

            ckd_move = ckd_moves[0]

            ckd_lines = ckd_move.move_line_ids.filtered(
                lambda ml: ml.lot_id and ml.qty_done == 0
            )

            if len(ckd_lines) < qty_to_produce:
                raise UserError(_("Not enough CKD lots to complete the production."))

            # ==============================
            # 2) MOVIMIENTO DE PRODUCTO TERMINADO
            # ==============================
            finished_move = production.move_finished_ids.filtered(
                lambda m: m.product_id == product
            )

            # ==============================
            # 3) PRODUCIR 1 UNIDAD POR CADA CKD
            # ==============================
            for i in range(qty_to_produce):

                ckd_line = ckd_lines[i]
                ckd_lot = ckd_line.lot_id

                # 3.1 Crear lote del producto terminado
                finished_lot = self.env['stock.lot'].create({
                    'product_id': product.id,
                    'company_id': production.company_id.id,
                    'name': ckd_lot.name,
                })

                # 3.2 Línea de producto terminado
                finished_ml = finished_move.move_line_ids.filtered(
                    lambda ml: not ml.lot_id and ml.qty_done == 0
                )[:1]

                if finished_ml:
                    finished_ml = finished_ml[0]
                else:
                    vals = finished_move._prepare_move_line_vals(quantity=0)
                    finished_ml = self.env['stock.move.line'].create(vals)

                finished_ml.write({
                    'qty_done': 1,
                    'lot_id': finished_lot.id,
                    'production_id': production.id,
                })

                # 3.3 Consumir CKD (1 a 1)
                ckd_line.write({
                    'qty_done': 1,
                    'production_id': production.id,
                })

                production.qty_producing += 1

            # ==============================
            # 4) ESTADO
            # ==============================
            if production.qty_producing >= production.product_qty:
                production.state = 'to_close'

        return True


class StockLot(models.Model):
    _inherit = 'stock.lot'

    attachment_ids = fields.Many2many('ir.attachment')