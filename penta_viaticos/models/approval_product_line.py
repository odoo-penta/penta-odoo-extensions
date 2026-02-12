# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ApprovalProductLine(models.Model):
    _inherit = "approval.product.line"

    viaticos_date = fields.Date(string="Fecha")

    viaticos_importe_solicitado = fields.Monetary(
        string="Importe solicitado",
        currency_field="currency_id",
    )

    viaticos_importe_permitido = fields.Monetary(
        string="Importe permitido",
        currency_field="currency_id",
        related="product_id.importe_permitido",
        store=True,
        readonly=True,
    )

    viaticos_total_solicitado = fields.Monetary(
        string="Total solicitado",
        currency_field="currency_id",
        compute="_compute_viaticos_totals",
        store=True,
    )

    viaticos_total_permitido = fields.Monetary(
        string="Total permitido",
        currency_field="currency_id",
        compute="_compute_viaticos_totals",
        store=True,
    )

    viaticos_paid_by = fields.Selection(
        [
            ("employee", "Empleado (a reembolsar)"),
            ("company", "Empresa"),
        ],
        string="Pagado por",
        default="company",
    )

    currency_id = fields.Many2one(
        related="approval_request_id.company_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.depends("quantity", "viaticos_importe_solicitado", "viaticos_importe_permitido")
    def _compute_viaticos_totals(self):
        for line in self:
            qty = line.quantity or 0.0
            line.viaticos_total_solicitado = qty * (line.viaticos_importe_solicitado or 0.0)
            line.viaticos_total_permitido = qty * (line.viaticos_importe_permitido or 0.0)

    @api.constrains("viaticos_importe_solicitado", "viaticos_importe_permitido")
    def _check_viaticos_importe(self):
        for line in self:
            req = line.approval_request_id
            if req and req.category_id.viaticos_control:
                # Si hay permitido (no 0), no permitir superar
                if (line.viaticos_importe_permitido or 0.0) and (line.viaticos_importe_solicitado or 0.0) > (line.viaticos_importe_permitido or 0.0):
                    raise ValidationError(_("El Importe solicitado no puede ser mayor al Importe permitido."))

    @api.onchange("product_id")
    def _onchange_product_id_viaticos_domain(self):
        """Si control activo: solo productos expensables."""
        req = self.approval_request_id
        if req and req.category_id.viaticos_control:
            return {"domain": {"product_id": [("can_be_expensed", "=", True)]}}
        return {}

    @api.constrains("product_id", "approval_request_id")
    def _check_viaticos_product_is_expense(self):
        for line in self:
            req = line.approval_request_id
            if req and req.category_id.viaticos_control and line.product_id and not line.product_id.can_be_expensed:
                raise ValidationError(
                    _("Solo se permiten productos de tipo gasto cuando la categoria tiene activo el control de viaticos.")
                )

    def _viaticos_paid_by_label(self, value):
        return dict(self._fields["viaticos_paid_by"].selection).get(value, value or "-")

    def _viaticos_line_summary(self):
        self.ensure_one()
        return _(
            "Producto: %(product)s | Fecha: %(date)s | Cantidad: %(qty)s | "
            "Solicitado: %(sol)s | Permitido: %(perm)s | Pagado por: %(paid)s"
        ) % {
            "product": self.product_id.display_name or "-",
            "date": self.viaticos_date or "-",
            "qty": self.quantity or 0.0,
            "sol": self.viaticos_importe_solicitado or 0.0,
            "perm": self.viaticos_importe_permitido or 0.0,
            "paid": self._viaticos_paid_by_label(self.viaticos_paid_by),
        }

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            req = line.approval_request_id
            if req and req.category_id.viaticos_control:
                req.message_post(body=_("Linea de viaticos creada. %s") % line._viaticos_line_summary())
        return lines

    def write(self, vals):
        tracked_fields = {
            "product_id",
            "viaticos_date",
            "quantity",
            "viaticos_importe_solicitado",
            "viaticos_importe_permitido",
            "viaticos_paid_by",
            "description",
        }
        before = {
            line.id: line._viaticos_line_summary()
            for line in self
            if line.approval_request_id and line.approval_request_id.category_id.viaticos_control
        }
        res = super().write(vals)
        if tracked_fields.intersection(vals.keys()):
            for line in self:
                req = line.approval_request_id
                if req and req.category_id.viaticos_control and line.id in before:
                    req.message_post(
                        body=_("Linea de viaticos actualizada.<br/>Antes: %(before)s<br/>Despues: %(after)s")
                        % {"before": before[line.id], "after": line._viaticos_line_summary()}
                    )
        return res

    def unlink(self):
        messages = []
        for line in self:
            req = line.approval_request_id
            if req and req.category_id.viaticos_control:
                messages.append((req, _("Linea de viaticos eliminada. %s") % line._viaticos_line_summary()))
        res = super().unlink()
        for req, message in messages:
            req.message_post(body=message)
        return res
