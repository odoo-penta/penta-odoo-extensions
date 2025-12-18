# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    cpn_prefix = fields.Char(string="Prefijo CPN", size=1)
    cpn_sequence_id = fields.Many2one("ir.sequence", string="Secuencia CPN",
                                      help="Secuencia numérica de 8 dígitos para CPN.")
    pdi_sequence_id = fields.Many2one("ir.sequence", string="Secuencia PDI",
                                      help="Secuencia numérica de 8 dígitos para PDI.")
    cpn_last_number = fields.Char(string="Último CPN generado", readonly=True, copy=False)
    pdi_last_number = fields.Char(string="Último PDI generado", readonly=True, copy=False)

    @api.constrains("cpn_prefix")
    def _check_cpn_prefix(self):
        for rec in self:
            if rec.cpn_prefix and len(rec.cpn_prefix) != 1:
                raise ValidationError(_("El prefijo CPN debe tener exactamente 1 carácter."))


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cpn_prefix = fields.Char(related="company_id.cpn_prefix", readonly=False)
    cpn_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Secuencia CPN",
        related="company_id.cpn_sequence_id",
        readonly=False,
        domain="[('padding','=',8)]",
        help="Usa padding=8."
    )
    pdi_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Secuencia PDI",
        related="company_id.pdi_sequence_id",
        readonly=False,
        domain="[('padding','=',8)]",
        help="Usa padding=8."
    )

    def set_values(self):
        res = super().set_values()
        if self.cpn_sequence_id and self.cpn_sequence_id.padding != 8:
            self.cpn_sequence_id.padding = 8
        if self.pdi_sequence_id and self.pdi_sequence_id.padding != 8:
            self.pdi_sequence_id.padding = 8
        return res

    @api.model
    def get_values(self):
        vals = super().get_values()
        company = self.env.company
        if not company.cpn_sequence_id:
            company.cpn_sequence_id = self.env.ref("penta_mrp_auto_process_all.seq_cpn_default")
        if not company.pdi_sequence_id:
            company.pdi_sequence_id = self.env.ref("penta_mrp_auto_process_all.seq_pdi_default")
        return vals
