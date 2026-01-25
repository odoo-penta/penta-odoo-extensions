# -*- coding: utf-8 -*-
import io
import base64
from datetime import date, datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.tools.misc import xlsxwriter  # Odoo ya lo expone
try:
    from odoo.addons.penta_base.reports.xlsx_formats import get_xlsx_formats
except Exception:  # si no está instalado penta_base
    get_xlsx_formats = None


def _first_day_of_current_month(env):
    today = fields.Date.context_today(env.user)
    if isinstance(today, str):
        y, m, d = map(int, today.split("-"))
        today = date(y, m, d)
    return today.replace(day=1)


class PentaImportReportWizard(models.TransientModel):
    _name = "penta.import.report.wizard"
    _description = "Wizard: Reporte de importaciones a Excel"

    date_from = fields.Date("Fecha inicio", required=True, default=lambda self: _first_day_of_current_month(self.env))
    date_to = fields.Date("Fecha fin", required=True, default=lambda self: fields.Date.context_today(self))
    field_ids = fields.Many2many(
        "penta.import.report.field",
        "penta_import_report_wizard_field_rel",
        "wizard_id", "field_id",
        string="Campos a incluir",
        domain=[("active", "=", True)],
        required=True,
    )
    select_all = fields.Boolean("Seleccionar todos")
    import_id = fields.Many2one("x.import", string="Número de importación")

    @api.onchange("select_all")
    def _onchange_select_all(self):
        if self.select_all:
            self.field_ids = self.env["penta.import.report.field"].search([("active", "=", True)])
        else:
            self.field_ids = [(5, 0, 0)]

    # ----------------- Validaciones -----------------
    def _validate_dates(self):
        if not self.date_from or not self.date_to:
            raise UserError(_("Debes establecer fecha de inicio y de fin."))
        if self.date_from > self.date_to:
            raise UserError(_("La fecha inicio no puede ser mayor que la fecha fin."))

    # ----------------- Helpers -----------------
    def _safe_get(self, obj, path):
        try:
            val = obj
            for p in path.split("."):
                if not val:
                    return ""
                val = getattr(val, p, False)
                if hasattr(val, "ids") and len(val) > 1:
                    val = val[:1]
            if hasattr(val, "ids"):
                return val.display_name or ""
            return "" if val in (False, None) else val
        except Exception:
            return ""

    def _context_map(self, line):
        po = line.order_id
        product = line.product_id
        partner = po.partner_id
        import_rec = getattr(po, "id_import", False)  # purchase.order.id_import -> x.import
        return {
            "line": line,
            "po": po,
            "product": product,
            "partner": partner,
            "import_rec": import_rec,
        }

    def _eval_expr(self, line, expr):
        ctx = self._context_map(line)
        prefixes = ["line.", "po.", "product.", "partner.", "import_rec."]
        if any(expr.startswith(p) for p in prefixes):
            base_key, rest = expr.split(".", 1)
            return self._safe_get(ctx.get(base_key), rest)
        return self._safe_get(ctx["line"], expr)

    # ---------- Facturas vinculadas a la línea ----------
    def _invoices_for_line(self, line):
        aml = self.env["account.move.line"].search([
            ("purchase_line_id", "=", line.id),
            ("move_id.state", "!=", "cancel"),
            ("move_id.move_type", "in", ["in_invoice", "in_refund"]),
        ])
        return aml.mapped("move_id")

    def _compute_invoice_name(self, line):
        inv = self._invoices_for_line(line)[:1]
        return inv.name if inv else ""

    def _compute_invoice_date(self, line):
        inv = self._invoices_for_line(line)[:1]
        return inv.invoice_date if inv else ""

    def _compute_invoice_amount_total(self, line):
        inv = self._invoices_for_line(line)[:1]
        return inv.amount_total if inv else 0.0

    # ---------- Pagos (último) ----------
    def _is_receivable_or_payable_ml(self, ml):
        """Devuelve True si la línea contable es de cuentas por cobrar/pagar.
        Compatible con Odoo 14→18 (cambios de campos)."""
        # 1) En move line existe (en versiones nuevas) el computado:
        ait = getattr(ml, "account_internal_type", False)
        if ait in ("receivable", "payable"):
            return True

        # 2) Campo antiguo en account.account (Odoo <16)
        acc = ml.account_id
        if acc:
            old_it = getattr(acc, "internal_type", False)
            if old_it in ("receivable", "payable"):
                return True

            # 3) Campo nuevo en account.account (Odoo 16+)
            new_at = getattr(acc, "account_type", False)
            if new_at in ("asset_receivable", "liability_payable"):
                return True

            # 4) Fallback vía user_type_id (por si acaso)
            ut = getattr(acc, "user_type_id", False)
            if ut:
                # Algunas versiones tienen 'type' con 'receivable'/'payable'
                ut_type = getattr(ut, "type", False)
                if ut_type in ("receivable", "payable"):
                    return True

        return False


    def _payments_for_invoices(self, invoices):
        Payment = self.env["account.payment"]
        payments = Payment.browse()

        for inv in invoices:
            # Tomamos SOLO líneas de cuenta por cobrar/pagar (partner lines)
            partner_lines = inv.line_ids.filtered(lambda l: self._is_receivable_or_payable_ml(l))

            for ml in partner_lines:
                # matched_debit_ids / matched_credit_ids siguen siendo la forma
                # más segura de encontrar pagos reconciliados en todas las versiones.
                for pr in (ml.matched_debit_ids + ml.matched_credit_ids):
                    other_ml = pr.debit_move_id if pr.credit_move_id == ml else pr.credit_move_id
                    if other_ml.payment_id:
                        payments |= other_ml.payment_id

        return payments

    def _compute_payment_last(self, line, field_kind):
        invoices = self._invoices_for_line(line)
        if not invoices:
            return ""
        pays = self._payments_for_invoices(invoices).sorted("date")
        if not pays:
            return ""
        p = pays[-1]
        if field_kind == "date":
            return p.date
        if field_kind == "method":
            return p.payment_method_line_id.display_name or ""
        if field_kind == "name":
            return p.name or ""
        if field_kind == "journal":
            return p.journal_id.display_name or ""
        return ""

    def _compute_payment_last_date(self, line): return self._compute_payment_last(line, "date")
    def _compute_payment_last_method(self, line): return self.import_id.payment_method_id.display_name
    def _compute_payment_last_name(self, line): return self.import_id.payment_reference
    def _compute_payment_last_journal(self, line): return self.import_id.journal_id.display_name

    # ---------- Cantidad ----------
    def _compute_qty_any(self, line):
        return getattr(line, "product_qty", 0.0) or getattr(line, "product_uom_qty", 0.0) or 0.0

    # ---------- Atributos de variantes (Categoría, Tipo, Año, Color) ----------
    def _get_attr_value(self, product, attr_name):
        """Devuelve el valor de un atributo por nombre exacto (p. ej. 'Categoria', 'Tipo', 'Año', 'Color')."""
        # product.product -> product_template_attribute_value_ids -> attribute_id.name / name
        p = product
        if not p:
            return ""
        # Odoo 16-18: product_template_attribute_value_ids.mapped('attribute_id.name')
        for ptav in p.product_template_attribute_value_ids:
            if (ptav.attribute_id and (ptav.attribute_id.name or "").strip().lower() == (attr_name or "").strip().lower()):
                # Mostrar nombre del valor
                return ptav.name or ptav.product_attribute_value_id.name or ""
        # Fallback: leer en plantilla (por si el producto no es variante)
        for line in p.product_tmpl_id.attribute_line_ids:
            if (line.attribute_id and (line.attribute_id.name or "").strip().lower() == (attr_name or "").strip().lower()):
                vals = line.value_ids
                return vals[:1].name if vals else ""
        return ""

    def _compute_attr_categoria(self, line): return self._get_attr_value(line.product_id, "Categoria")
    def _compute_attr_tipo(self, line):       return self._get_attr_value(line.product_id, "Tipo")
    def _compute_attr_anio(self, line):       return self._get_attr_value(line.product_id, "Año")
    def _compute_attr_color(self, line):      return self._get_attr_value(line.product_id, "Color")

    # ---------- Landed costs prorrateados por línea ----------
    def _valuation_lines_for_line(self, line):
        StockMove = self.env["stock.move"]
        moves = StockMove.search([("purchase_line_id", "=", line.id), ("state", "=", "done")])
        return self.env["stock.valuation.adjustment.lines"].search([("move_id", "in", moves.ids)])

    def _compute_lc_component(self, line, component):  # 'freight'|'insurance'|'customs'
        vals = self._valuation_lines_for_line(line)
        total = 0.0
        for v in vals:
            cl = v.cost_line_id
            if not cl or not cl.product_id or not cl.product_id.product_tmpl_id:
                continue
            lctype = getattr(cl.product_id.product_tmpl_id, "landed_cost_type", "") or ""
            if lctype == component:
                total += v.additional_landed_cost or 0.0
        return total

    def _compute_lc_freight(self, line):   return self._compute_lc_component(line, "freight")
    def _compute_lc_insurance(self, line): return self._compute_lc_component(line, "insurance")
    def _compute_lc_customs(self, line):   return self._compute_lc_component(line, "customs")

    # ---------- Impuestos de destino (Ad Valorem, Fodinfa, ICE, Recargo, Interés) ----------
    def _compute_lc_tax(self, line, wanted):
        import_rec = getattr(line.order_id, "id_import", False)
        if not import_rec:
            return 0.0
        lcs = self.env["stock.landed.cost"].search([("id_import", "=", import_rec.id)])
        total = 0.0
        w = (wanted or "").lower()
        for lc in lcs:
            for tl in lc.tax_lines.filtered(lambda r: r.product_id == line.product_id):
                name = (tl.cost_line or "").lower()
                if w in name:
                    total += tl.tax_value or 0.0
        return total

    def _compute_lc_tax_adval(self, line):   return self._compute_lc_tax(line, "ad valorem")
    def _compute_lc_tax_fodinfa(self, line): return self._compute_lc_tax(line, "fodinfa")
    def _compute_lc_tax_ice(self, line):     return self._compute_lc_tax(line, "ice")
    def _compute_lc_tax_recargo(self, line): return self._compute_lc_tax(line, "recargo")
    def _compute_lc_tax_interes(self, line): return self._compute_lc_tax(line, "interes")

    def _compute_total_aranceles(self, line):
        return (
            self._compute_lc_tax_adval(line)
            + self._compute_lc_tax_fodinfa(line)
            + self._compute_lc_tax_ice(line)
            + self._compute_lc_tax_recargo(line)
        )

    # ---------- CFR / CIF ----------
    def _compute_cfr(self, line):
        # CFR = total por producto en la OC + costo en destino 'Flete'
        return (line.price_subtotal or 0.0) + self._compute_lc_freight(line)

    def _compute_cif(self, line):
        # CIF = CFR + costo en destino 'Seguro'
        return self._compute_cfr(line) + self._compute_lc_insurance(line)

    # ---------- IVA de factura (líneas cuyo producto es costo de aduana) ----------
    def _compute_iva_customs(self, line):
        invoices = self._invoices_for_line(line)
        if not invoices:
            return 0.0

        def is_iva_tax(tax):
            name = (tax.name or "").upper()
            group = (tax.tax_group_id.name or "").upper() if tax.tax_group_id else ""
            return "IVA" in name or "IVA" in group

        total_tax = 0.0
        for inv in invoices:
            currency = inv.currency_id or self.env.company.currency_id
            for il in inv.invoice_line_ids.filtered(lambda l: l.product_id and getattr(l.product_id.product_tmpl_id, "landed_cost_type", "") == "customs"):
                # Calcular impuestos de la línea
                res = il.tax_ids.compute_all(
                    il.price_unit,
                    currency=currency,
                    quantity=il.quantity,
                    product=il.product_id,
                    partner=inv.partner_id,
                )
                for t in res.get("taxes", []):
                    tax = self.env["account.tax"].browse(t.get("id"))
                    if is_iva_tax(tax):
                        total_tax += t.get("amount", 0.0)
        return total_tax

    # ---------- CIF total desde tabla taxes (por completitud) ----------
    def _compute_lc_cif_total(self, line):
        import_rec = getattr(line.order_id, "id_import", False)
        if not import_rec:
            return 0.0
        lcs = self.env["stock.landed.cost"].search([("id_import", "=", import_rec.id)])
        total = 0.0
        for lc in lcs:
            for tl in lc.tax_lines.filtered(lambda r: r.product_id == line.product_id):
                total += tl.cif or 0.0
        return total

    def _compute_aranceles_mas_interes(self, line):
        return self._compute_total_aranceles(line) + self._compute_lc_tax_interes(line)

    def _get_selection_label(self, rec, field_name):
        """Devuelve la etiqueta (traducida) del campo selection."""
        if not rec:
            return ""
        field = rec._fields.get(field_name)
        val = rec[field_name]
        if not field:
            return val or ""
        if field.type == "selection":
            selection = field.selection(rec) if callable(field.selection) else field.selection
            for key, label in selection:
                if key == val:
                    return _(label)  # usa traducciones si existen
        return val or ""

    # --- Helpers de facturas por importación ---
    def _invoices_for_import(self, import_rec):
        """Facturas de proveedor asociadas a una importación (id_import)."""
        if not import_rec:
            return self.env["account.move"].browse()
        return self.env["account.move"].search([
            ("id_import", "=", import_rec.id),
            ("state", "!=", "cancel"),
            ("move_type", "in", ["in_invoice", "in_refund"]),
        ])

    def _sum_subtotal_by_classification(self, line, wanted_code):
        """
        Suma el price_subtotal de las líneas de facturas (sin impuestos)
        de productos cuya plantilla tenga type_classification == wanted_code.
        Notas de crédito (in_refund) restan.
        """
        import_rec = getattr(line.order_id, "id_import", False)
        moves = self._invoices_for_import(import_rec)
        total = 0.0
        for inv in moves:
            sign = -1.0 if inv.move_type == "in_refund" else 1.0
            for il in inv.invoice_line_ids:
                pt = il.product_id.product_tmpl_id if il.product_id else False
                if pt and (pt.type_classification or "") == wanted_code:
                    total += sign * (il.price_subtotal or 0.0)
        return total

    # --- Wrappers específicos ---
    def _compute_from_invoices_ad_valorem(self, line):
        return self._sum_subtotal_by_classification(line, "ad_valorem")

    def _compute_from_invoices_fodinfa(self, line):
        return self._sum_subtotal_by_classification_lineaware(line, "fodinfa")

    def _compute_from_invoices_ice(self, line):
        return self._sum_subtotal_by_classification(line, "ice")

    def _compute_from_invoices_recargo_ice(self, line):
        return self._sum_subtotal_by_classification(line, "recargo_ice")

    def _sum_subtotal_by_landed_cost_type(self, line, wanted_lct):
        """
        Suma price_subtotal de líneas de factura (sin impuestos)
        cuyos productos (plantilla) tengan landed_cost_type == wanted_lct.
        Notas de crédito restan.
        """
        import_rec = getattr(line.order_id, "id_import", False)
        moves = self._invoices_for_import(import_rec)
        total = 0.0
        for inv in moves:
            sign = -1.0 if inv.move_type == "in_refund" else 1.0
            for il in inv.invoice_line_ids:
                tmpl = il.product_id.product_tmpl_id if il.product_id else False
                if tmpl and (tmpl.landed_cost_type or "") == wanted_lct:
                    total += sign * (il.price_subtotal or 0.0)
        return total

    def _compute_total_aranceles_from_invoices_customs(self, line):
        """Total Aranceles = suma de subtotales de ítems 'Costo de aduana' en facturas de la IG."""
        return self._sum_subtotal_by_landed_cost_type(line, "customs")

    def _compute_iva_from_flagged_products(self, line):
        """
        IVA = suma de los montos de impuestos (tax_ids) de las líneas de factura
        cuyos productos tienen product.template.import_iva_flag = True.
        Solo impuestos (no subtotal). NC restan.
        """
        import_rec = getattr(line.order_id, "id_import", False)
        moves = self._invoices_for_import(import_rec)
        total_tax = 0.0

        for inv in moves:
            sign = -1.0 if inv.move_type == "in_refund" else 1.0
            currency = inv.currency_id or self.env.company.currency_id
            partner = inv.partner_id

            for il in inv.invoice_line_ids:
                # omitir notas/separadores
                if getattr(il, "display_type", False):
                    continue
                tmpl = il.product_id.product_tmpl_id if il.product_id else False
                if not (tmpl and tmpl.import_iva_flag):
                    continue

                # calcular impuestos de la línea
                taxes_res = il.tax_ids.compute_all(
                    il.price_unit * (1.0 - (il.discount or 0.0) / 100.0),
                    currency=currency,
                    quantity=il.quantity or 0.0,
                    product=il.product_id,
                    partner=partner,
                )
                line_tax_amount = sum(t.get("amount", 0.0) for t in taxes_res.get("taxes", []))
                total_tax += sign * line_tax_amount

        return total_tax

    def _sum_subtotal_by_classification_lineaware(self, line, wanted_code):
        """
        Suma por línea de compra:
        1) Si hay líneas de factura con type_classification=wanted_code y MISMO producto
        (o misma plantilla) que la línea de compra, suma solo esas.
        2) Si NO hay coincidencias (caso línea agregada), prorratea el total de la
        importación según el price_subtotal de la PO line.
        """
        import_rec = getattr(line.order_id, "id_import", False)
        moves = self._invoices_for_import(import_rec)
        if not moves:
            return 0.0

        total_same_product = 0.0
        total_classif_all = 0.0

        for inv in moves:
            sign = -1.0 if inv.move_type == "in_refund" else 1.0
            for il in inv.invoice_line_ids:
                pt = il.product_id.product_tmpl_id if il.product_id else False
                if not (pt and (pt.type_classification or "") == wanted_code):
                    continue
                amt = sign * (il.price_subtotal or 0.0)
                total_classif_all += amt
                # Coincidencia por product o por plantilla
                if (il.product_id and il.product_id == line.product_id) or \
                (il.product_id and il.product_id.product_tmpl_id == line.product_id.product_tmpl_id):
                    total_same_product += amt

        # Caso 1: hay líneas por el MISMO producto → devolver solo esas (por-línea real)
        if total_same_product:
            return total_same_product

        # Caso 2: no hay coincidencias → prorrateo por subtotal de la OC
        if not total_classif_all:
            return 0.0

        po_lines = self.env["purchase.order.line"].search([
            ("order_id.id_import", "=", import_rec.id),
            ("order_id.state", "in", ["purchase", "done"]),
        ])
        base_total = sum((l.price_subtotal or 0.0) for l in po_lines) or 0.0
        if base_total <= 0.0:
            return 0.0

        share = (line.price_subtotal or 0.0) / base_total
        return total_classif_all * share

    def _compute_type_of_load_es(self, line):
        import_rec = getattr(line.order_id, "id_import", False)
        # fallback por si tus claves tienen typos (“loose cargoe”):
        label = self._get_selection_label(import_rec, "type_of_load")
        if not label:
            mapping = {
                "containerized": "Contenerizada",
                "loose cargoe": "Carga suelta",
                "loose_cargo": "Carga suelta",
            }
            return mapping.get(getattr(import_rec, "type_of_load", "") or "", "")
        return label

    def _compute_total_aranceles_from_components(self, line):
        return (
            (self._compute_from_invoices_ad_valorem(line) or 0.0) +
            (self._compute_from_invoices_fodinfa(line) or 0.0) +
            (self._compute_from_invoices_ice(line) or 0.0) +
            (self._compute_from_invoices_recargo_ice(line) or 0.0)
        )

    # =========================
    #  Helpers compartidos
    # =========================

    def _collect_pickings_for_import(self, import_rec):
        """Pickings derivados de las OC de la importación (incluye casos sin purchase_id directo)."""
        if not import_rec:
            return self.env["stock.picking"].browse()
        pos = self.env["purchase.order"].search([("id_import", "=", import_rec.id)])
        pick1 = self.env["stock.picking"].search([("purchase_id", "in", pos.ids)])
        mls = self.env["stock.move"].search([("purchase_line_id.order_id", "in", pos.ids)])
        pick2 = mls.mapped("picking_id")
        return (pick1 | pick2)

    def _landed_costs_for_import(self, import_rec):
        """Landed Costs relacionados a los pickings de la importación (y, si hace falta, por valuation lines)."""
        StockLandedCost = self.env["stock.landed.cost"]
        if not import_rec:
            return StockLandedCost.browse()
        pickings = self._collect_pickings_for_import(import_rec)
        lcs = StockLandedCost.search([("picking_ids", "in", pickings.ids)])
        if not lcs:
            val_lines = self.env["stock.valuation.adjustment.lines"].search([
                ("move_id.picking_id", "in", pickings.ids)
            ])
            if val_lines:
                lcs |= val_lines.mapped("cost_id")
        return lcs

    def _is_unassigned_lct_value(self, val):
        """True si landed_cost_type está 'no asignado' (False/''/none/unassigned)."""
        return (not val) or (str(val).strip().lower() in {"none", "unassigned"})

    def _get_import_po_lines(self, import_rec):
        return self.env["purchase.order.line"].search([
            ("order_id.id_import", "=", import_rec.id),
            ("order_id.state", "in", ["purchase", "done"]),
        ])

    def _compute_ad_valorem_prorated(self, line):
        """
        Ad Valorem PRORRATEADO:
        1) Total Ad Valorem (facturas) a nivel de importación.
        2) Reparto proporcional al price_subtotal de CADA línea de compra de la importación.
        """
        import_rec = getattr(line.order_id, "id_import", False)
        if not import_rec:
            return 0.0

        # (1) Total a nivel importación (solo líneas con clasificación ad_valorem)
        total_adval = 0.0
        for inv in self._invoices_for_import(import_rec):
            sign = -1.0 if inv.move_type == "in_refund" else 1.0
            for il in inv.invoice_line_ids:
                if getattr(il, "display_type", False):
                    continue
                pt = il.product_id.product_tmpl_id if il.product_id else False
                if pt and getattr(pt, "type_classification", "") == "ad_valorem":
                    total_adval += sign * (il.price_subtotal or 0.0)

        if not total_adval:
            return 0.0

        # (2) Base de prorrateo = suma de subtotales de TODAS las líneas de OC de la importación
        po_lines = self._get_import_po_lines(import_rec)
        base = sum((l.price_subtotal or 0.0) for l in po_lines) or 0.0
        if base <= 0.0:
            # Fallback por cantidad si no hubiera base de valor
            base = sum((l.product_qty or 0.0) for l in po_lines) or 0.0
            if base <= 0.0:
                return 0.0
            share = (line.product_qty or 0.0) / base
        else:
            share = (line.price_subtotal or 0.0) / base

        return total_adval * share

    def _compute_other_costs_unassigned_lct(self, line):
        """
        'Otros costos' por LÍNEA:
        1) Agrupar por PRODUCTO el additional_landed_cost de valuation lines de los LC
        de la importación, solo cuando el CONCEPTO (cost_line_id.product_id) NO tiene
        landed_cost_type asignado (otros).
        2) PRORRATEAR el total de ese producto entre las PO lines del MISMO producto
        dentro de la importación, proporcional a price_subtotal (o cantidad).
        """
        import_rec = getattr(line.order_id, "id_import", False)
        if not import_rec or not line.product_id:
            return 0.0

        product = line.product_id
        tmpl = product.product_tmpl_id

        # 1) Total de ajustes de valoración (additional_landed_cost) para ESTE producto
        lcs = self._landed_costs_for_import(import_rec)
        if not lcs:
            return 0.0

        total_for_product = 0.0
        for lc in lcs:
            # valuation lines del LC para el producto exacto
            vlines = lc.valuation_adjustment_lines.filtered(lambda vl: vl.product_id == product)
            if not vlines:
                continue
            for vl in vlines:
                # filtrar SOLO “otros”: concepto sin landed_cost_type
                cl = getattr(vl, "cost_line_id", False)
                prod_concepto = getattr(cl, "product_id", False) if cl else False
                pt = prod_concepto.product_tmpl_id if prod_concepto else False
                lct = getattr(pt, "landed_cost_type", False) if pt else False
                if pt and not self._is_unassigned_lct_value(lct):
                    continue

                add_cost = 0.0
                for fname in ("additional_landed_cost", "added_cost"):
                    if hasattr(vl, fname) and getattr(vl, fname):
                        add_cost = float(getattr(vl, fname) or 0.0)
                        break
                total_for_product += add_cost

        if total_for_product == 0.0:
            return 0.0

        # 2) PRORRATEO entre PO lines del MISMO producto dentro de la importación
        #    (si tienes varias líneas con el mismo producto, evitamos repetir el total en cada una)
        po_lines_same_product = self._get_import_po_lines(import_rec).filtered(
            lambda l: l.product_id == product
        )
        # ---- Por VALOR (price_subtotal). Si prefieres por cantidad, ver comentarios abajo.
        base = sum((l.price_subtotal or 0.0) for l in po_lines_same_product) or 0.0
        if base <= 0.0:
            # fallback por cantidades si no hay base de valor
            base = sum((l.product_qty or 0.0) for l in po_lines_same_product) or 0.0
            if base <= 0.0:
                return 0.0
            share = (line.product_qty or 0.0) / base
        else:
            share = (line.price_subtotal or 0.0) / base

        return total_for_product * share
    
    # ----------------- Exportación -----------------

    def _compute_total_importacion(self, line):
        """
        Total importación = Total Aranceles + Otros Costos + CIF
        (todos por línea    ).
        Usa los métodos ya existentes; si alguno no existe, toma 0.0.
        """
        # Total Aranceles
        m_aranceles = getattr(self, "_compute_total_aranceles_from_components", None)
        total_aranceles = float(m_aranceles(line)) if m_aranceles else 0.0

        # Otros Costos
        m_otros = getattr(self, "_compute_other_costs_unassigned_lct", None)
        otros_costos = float(m_otros(line)) if m_otros else 0.0

        # CIF (ajusta el nombre si tu método se llama distinto)
        m_cif = (
            getattr(self, "_compute_cif", None)
            or getattr(self, "_compute_cif_from_invoices", None)
            or getattr(self, "_compute_cif_value", None)
        )
        cif_val = float(m_cif(line)) if m_cif else 0.0

        return (total_aranceles or 0.0) + (otros_costos or 0.0) + (cif_val or 0.0)

    def action_export_xlsx(self):

        if not self.import_id:
            self._validate_dates()

        if not xlsxwriter:
            raise UserError(_("No se encontró 'xlsxwriter'. Instálalo en el servidor."))

        # Dataset: líneas de compra cuya importación tenga fecha dentro del rango
        pol_obj = self.env["purchase.order.line"]
        if self.import_id:
            domain = [
                ("order_id.id_import", "=", self.import_id.id),
                ("order_id.state", "in", ["purchase", "done"]),
            ]
        else:
            domain = [
                ("order_id.id_import.date", ">=", self.date_from),
                ("order_id.id_import.date", "<=", self.date_to),
                ("order_id.state", "in", ["purchase", "done"]),
            ]
        lines = pol_obj.search(domain, order="order_id, id")
        if not lines:
            raise UserError(_("No hay líneas de compra (con importación) en el rango seleccionado."))

        fields_cfg = self.field_ids.sorted(key=lambda f: (f.sequence, f.id))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        ws = workbook.add_worksheet("Importaciones")

        # ===== Estilos =====
        formats = {}
        if get_xlsx_formats:
            try:
                formats = get_xlsx_formats(workbook) or {}
            except Exception:
                formats = {}
        # Fallback si no hay paquete de estilos
        def _fallback(fmt_dict):
            return workbook.add_format(fmt_dict)

        fmt_header = formats.get("header_bg") or _fallback({"bold": True, "bg_color": "#EEEEEE", "border": 1, "align": "center"})
        fmt_date   = formats.get("date")      or _fallback({"num_format": "yyyy-mm-dd", "border": 1})
        fmt_number = formats.get("number")    or _fallback({"num_format": "#,##0.00", "border": 1})
        fmt_text   = formats.get("border")    or _fallback({"border": 1})
        fmt_center = formats.get("center")    or _fallback({"align": "center", "valign": "vcenter", "border": 1})
        fmt_title  = formats.get("title")     or _fallback({"bold": True, "font_size": 14})
        fmt_subtle = formats.get("subtle")    or _fallback({})  # opcional
        #fmt_header = workbook.add_format({"bold": True})
        #fmt_date = workbook.add_format({"num_format": "yyyy-mm-dd"})
        #fmt_float = workbook.add_format({"num_format": "#,##0.00"})

        # Headers
        for col, f in enumerate(fields_cfg):
            ws.write(0, col, f.name, fmt_header)

        # Filas
        row = 1
        for line in lines:
            col = 0
            for f in fields_cfg:
                if f.compute_type == "expr":
                    value = self._eval_expr(line, f.field_expr)
                else:
                    m = getattr(self, f.method_name, None)
                    value = m(line) if m else ""

                if isinstance(value, (float, int)):
                    ws.write_number(row, col, float(value), fmt_number)
                elif isinstance(value, date):
                    dt = datetime.combine(value, datetime.min.time())
                    ws.write_datetime(row, col, dt, fmt_date)
                else:
                    # texto: si quieres centrar ciertos campos, puedes decidir aquí
                    ws.write(row, col, "" if value in (False, None) else value, fmt_text)
                col += 1
            row += 1

        workbook.close()
        xlsx_data = output.getvalue()
        output.close()

        fname = f"reporte_importaciones_{self.date_from}_{self.date_to}.xlsx"
        attachment = self.env["ir.attachment"].create({
            "name": fname,
            "type": "binary",
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "datas": base64.b64encode(xlsx_data),
            "res_model": self._name,
            "res_id": self.id,
        })
        return {"type": "ir.actions.act_url", "url": f"/web/content/{attachment.id}?download=1", "target": "self"}