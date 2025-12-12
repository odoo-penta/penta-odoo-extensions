# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class GenerateCpnPdiWizard(models.TransientModel):
    _name = "generate.cpn.pdi.wizard"
    _description = "Generar CPN y PDI para la OP"

    production_id = fields.Many2one("mrp.production", required=True, ondelete="cascade")
    move_line_id = fields.Many2one("stock.move.line", ondelete="set null")  

    cpn_preview = fields.Char(string="Siguiente CPN (preview)", compute="_compute_previews")
    pdi_start = fields.Char(string="PDI inicial (editable)", required=True)

    lotes_a_generar = fields.Integer(string="Lotes por generar", compute="_compute_lotes",
                                     help="Cantidad de líneas de producto terminado a numerar.")

    @api.depends("production_id", "move_line_id")
    def _compute_lotes(self):
        for w in self:
            if w.move_line_id:
                w.lotes_a_generar = 1
            else:
                w.lotes_a_generar = len(w.production_id._finished_move_lines_to_process())

    @api.depends("production_id")
    def _compute_previews(self):
        for w in self:
            company = w.production_id.company_id
            seq_cpn = company.cpn_sequence_id
            seq_pdi = company.pdi_sequence_id
            prefix = company.cpn_prefix or ""
            cpn_next = str(seq_cpn.number_next_actual).zfill(seq_cpn.padding or 8) if seq_cpn else ""
            pdi_next = str(seq_pdi.number_next_actual).zfill(seq_pdi.padding or 8) if seq_pdi else ""
            w.cpn_preview = f"{prefix}{cpn_next}" if cpn_next else ""
            w.pdi_start = pdi_next

    def _check_digits8(self, value, fieldlabel):
        if not value or not value.isdigit() or len(value) != 8:
            raise ValidationError(_("%s debe ser exactamente 8 dígitos numéricos.") % fieldlabel)

    def _lines_to_process(self):
        if self.move_line_id:
            return self.move_line_id
        return self.production_id._finished_move_lines_to_process()

    def action_confirm(self):
        self.ensure_one()
        prod = self.production_id
        company = prod.company_id

        if prod.state not in ("confirmed", "progress"):
            raise ValidationError(_("La orden debe estar en estado 'Listo' o 'En Progreso'."))

        seq_cpn = company.cpn_sequence_id
        seq_pdi = company.pdi_sequence_id
        prefix = (company.cpn_prefix or "").strip()

        if not seq_cpn or not seq_pdi:
            raise ValidationError(_("Configura las secuencias de CPN y PDI en Ajustes de Fabricación (HDU01)."))
        if prefix and len(prefix) != 1:
            raise ValidationError(_("El prefijo CPN debe tener exactamente 1 carácter."))

        self._check_digits8(self.pdi_start, "PDI inicial")
        pdi_start_int = int(self.pdi_start)
        if pdi_start_int > seq_pdi.number_next_actual:
            seq_pdi.sudo().write({"number_next": pdi_start_int, "number_next_actual": pdi_start_int})

        lines = self._lines_to_process()
        if not lines:
            raise ValidationError(_("No hay líneas de producto terminado con seguimiento por lote/serie para numerar."))

        generated = []
        for ml in lines:
            next_pdi_num = str(seq_pdi.next_by_id()).zfill(seq_pdi.padding or 8)
            next_cpn_num = str(seq_cpn.next_by_id()).zfill(seq_cpn.padding or 8)
            cpn_value = f"{prefix}{next_cpn_num}"
            pdi_value = next_pdi_num

            lot = ml.lot_id
            if not lot:
                lot = self.env["stock.lot"].create({
                    "name": pdi_value, 
                    "product_id": ml.product_id.id,
                    "company_id": prod.company_id.id,
                })
                ml.lot_id = lot.id

            # Guardar
            lot.write({
                "cpn": cpn_value,
                "pdi": pdi_value,
                "cpn_generated_at": fields.Datetime.now(),
                "pdi_generated_at": fields.Datetime.now(),
                "ramv": f"{cpn_value}-{pdi_value}" if "ramv" in lot else lot.ramv,  # si existe
            })
            generated.append((lot.name, cpn_value, pdi_value))

        company.write({
            "cpn_last_number": generated[-1][1] if generated else False,
            "pdi_last_number": generated[-1][2] if generated else False,
        })
        prod.write({"cpn_pdi_generated_at": fields.Datetime.now()})

        lines_txt = "<br/>".join([_("Línea/Lote %s → CPN %s / PDI %s") % (a, b, c) for (a, b, c) in generated])
        prod.message_post(body=_("Se generaron CPN/PDI (Process Lines):<br/>%s") % lines_txt)

        return {"type": "ir.actions.act_window_close"}