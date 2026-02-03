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

    product_is_serial = fields.Boolean(compute='_compute_product_is_serial')
    cpn_pdi_generated_at = fields.Datetime(string="CPN/PDI generated", readonly=True, copy=False)

    @api.depends('product_id')
    def _compute_product_is_serial(self):
        for rec in self:
            rec.product_is_serial = False
            if rec.product_id.tracking == 'serial' or rec.product_id.tracking == 'lot':
                rec.product_is_serial = True
    
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

class StockLot(models.Model):
    _inherit = 'stock.lot'

    attachment_ids = fields.Many2many('ir.attachment')
