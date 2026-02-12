# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    viaticos_city_origin_id = fields.Many2one(
        "res.country.state.city", string="Ciudad origen", tracking=True
    )
    viaticos_city_destination_id = fields.Many2one(
        "res.country.state.city", string="Ciudad destino", tracking=True
    )

    viaticos_employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado solicitante",
        compute="_compute_viaticos_employee",
        store=False,
    )

    viaticos_job_title = fields.Char(
        string="Cargo",
        compute="_compute_viaticos_job_title",
        store=False,
    )

    viaticos_total_employee = fields.Monetary(
        string="Total paga el empleado (a reembolsar)",
        currency_field="currency_id",
        compute="_compute_viaticos_totals",
        store=True,
        tracking=True,
    )

    viaticos_total_company = fields.Monetary(
        string="Total paga la empresa",
        currency_field="currency_id",
        compute="_compute_viaticos_totals",
        store=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.depends("request_owner_id")
    def _compute_viaticos_employee(self):
        """Obtiene empleado desde el usuario que solicita (request_owner_id)."""
        Employee = self.env["hr.employee"]
        for rec in self:
            employee = Employee.search([("user_id", "=", rec.request_owner_id.id)], limit=1)
            rec.viaticos_employee_id = employee

    @api.depends("viaticos_employee_id")
    def _compute_viaticos_job_title(self):
        for rec in self:
            emp = rec.viaticos_employee_id
            rec.viaticos_job_title = emp.job_title or emp.job_id.name or False

    @api.depends(
        "category_id.viaticos_control",
        "product_line_ids.quantity",
        "product_line_ids.viaticos_importe_solicitado",
        "product_line_ids.viaticos_paid_by",
    )
    def _compute_viaticos_totals(self):
        for rec in self:
            if not rec.category_id.viaticos_control:
                rec.viaticos_total_employee = 0.0
                rec.viaticos_total_company = 0.0
                continue

            employee_total = 0.0
            company_total = 0.0

            for line in rec.product_line_ids:
                total_line = (line.quantity or 0.0) * (line.viaticos_importe_solicitado or 0.0)
                if line.viaticos_paid_by == "employee":
                    employee_total += total_line
                elif line.viaticos_paid_by == "company":
                    company_total += total_line

            rec.viaticos_total_employee = employee_total
            rec.viaticos_total_company = company_total

    @api.onchange(
        "category_id",
        "viaticos_total_employee",
        "viaticos_total_company",
    )
    def _onchange_viaticos_set_amount(self):
        """Si hay totales de viaticos, reflejarlos en el campo importe."""
        for rec in self:
            if not rec.category_id.viaticos_control:
                continue
            total = (rec.viaticos_total_employee or 0.0) + (rec.viaticos_total_company or 0.0)
            rec.amount = total

    @api.onchange("category_id", "date_start", "date_end", "product_line_ids")
    def _onchange_viaticos_hospedaje_warning(self):
        """Advertencia no bloqueante si noches y hospedaje no coinciden."""
        for rec in self:
            if not rec.category_id.viaticos_control or not rec.date_start or not rec.date_end:
                continue

            nights = (rec.date_end.date() - rec.date_start.date()).days
            if nights <= 0:
                continue

            hospedaje_qty = 0.0
            for line in rec.product_line_ids:
                product = line.product_id
                if not product:
                    continue
                categ_name = (product.categ_id.complete_name or "").lower()
                product_name = (product.display_name or "").lower()
                if "hosped" in categ_name or "hosped" in product_name or "aloj" in product_name:
                    hospedaje_qty += line.quantity or 0.0

            if hospedaje_qty != float(nights):
                return {
                    "warning": {
                        "title": _("Advertencia de hospedaje"),
                        "message": _(
                            "El viaje cubre %(nights)s noche(s) y el detalle de hospedaje suma %(qty)s. "
                            "Revise los registros de hospedaje."
                        ) % {"nights": nights, "qty": hospedaje_qty},
                    }
                }

    def action_approve(self):
        for rec in self:
            if rec.category_id.viaticos_control:
                today = fields.Date.context_today(rec)
                date_from = rec.category_id.viaticos_date_from_allowed
                date_to = rec.category_id.viaticos_date_to_allowed

                if date_from and today < date_from:
                    raise UserError(_("No está permitido solicitar viáticos antes de %s.") % date_from)
                if date_to and today > date_to:
                    raise UserError(_("No está permitido solicitar viáticos después de %s.") % date_to)

        return super().action_approve()




