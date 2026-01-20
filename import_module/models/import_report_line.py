# -*- coding: utf-8 -*-
from odoo import api, models, fields
from dateutil.relativedelta import relativedelta


class PentaImportReportLine(models.Model):
    _name = "penta.import.report.line"
    _description = "Línea Reporte Importaciones"
    _order = "id desc"

    run_id = fields.Many2one(
        "penta.import.report.run",
        string="Ejecución",
        index=True,
        ondelete="cascade",
    )

    purchase_line_id = fields.Many2one("purchase.order.line", string="Línea OC", index=True)
    x_import_name = fields.Char(string="Importación")
    x_freight_agent = fields.Char(string="Embarcador")
    x_guide_bl = fields.Char(string="Guía de importación")
    x_containers_number = fields.Char(string="Número de contenedores")
    x_type_of_load = fields.Char(string="Tipo de carga")
    x_date_shipment = fields.Date(string="Fecha de guía de importación")
    x_eta = fields.Date(string="Fecha estimada de llegada")
    x_transit_time = fields.Char(string="Tiempo de tránsito")
    x_hazardous_load = fields.Char(string="Carga")
    x_incoterm = fields.Char(string="Incoterm")
    x_customs_regime = fields.Char(string="Tipo de régimen")
    x_real_eta = fields.Date(string="Fecha de llegada real")
    x_departure_port = fields.Date(string="Fecha de salida de puerto")
    x_free_days_ret = fields.Char(string="Días libres devolución contenedor")
    x_free_days_due = fields.Date(string="Fecha de vencimiento días libres")
    x_supplier_receipt_date = fields.Date(string="Fecha de recepción de proveedor")
    x_agent_send_date = fields.Date(string="Fecha envío agente")
    x_ins_pol_number = fields.Char(string="Número de póliza")
    x_virtual_bill = fields.Char(string="Facturación virtual")
    x_dai_field = fields.Char(string="DAI")
    x_liq_id = fields.Char(string="ID Liquidación")
    x_liq_date = fields.Date(string="Fecha de liquidación")

    x_po_line_name = fields.Char(string="Número de orden del proveedor")
    x_product = fields.Char(string="Producto")
    x_attr_categoria = fields.Char(string="Categoría")
    x_attr_tipo = fields.Char(string="Tipo")
    x_attr_anio = fields.Char(string="Año")
    x_attr_color = fields.Char(string="Color")
    x_sri_subcategory = fields.Char(string="Subcategoría SRI")
    x_qty = fields.Float(string="Cantidad", digits=(16, 2))
    x_price_unit = fields.Float(string="Valor unitario", digits=(16, 6))
    x_price_subtotal = fields.Float(string="Valor total", digits=(16, 2))

    x_lc_freight = fields.Float(string="Valor de flete", digits=(16, 2))
    x_lc_cif_insurance = fields.Float(string="Valor de seguro", digits=(16, 2))
    x_lc_tax_adval = fields.Float(string="Ad Valorem", digits=(16, 2))
    x_lc_tax_fod = fields.Float(string="Fodinfa", digits=(16, 2))
    x_lc_tax_ice = fields.Float(string="Ice", digits=(16, 2))
    x_lc_tax_recargo = fields.Float(string="Recargo Ice", digits=(16, 2))
    x_total_aranceles = fields.Float(string="Total Aranceles", digits=(16, 2))
    x_lc_tax_interes = fields.Float(string="Valor de interes", digits=(16, 2))
    x_total_aranceles_interes = fields.Float(string="Total aranceles + Valor de interés", digits=(16, 2))
    x_other_costs_unassigned_lct = fields.Float(string="Otros costos", digits=(16, 2))

    x_cfr = fields.Float(string="CFR", digits=(16, 2))
    x_cif = fields.Float(string="CIF", digits=(16, 2))
    x_iva_customs = fields.Float(string="IVA", digits=(16, 2))

    x_inv_number = fields.Char(string="Número de factura")
    x_inv_date = fields.Date(string="Fecha de factura")
    x_inv_total = fields.Float(string="Importe de factura", digits=(16, 2))

    x_pay_date = fields.Date(string="Fecha de pago")
    x_pay_method = fields.Char(string="Método de pago")
    x_pay_number = fields.Char(string="Número de pago")
    x_pay_journal = fields.Char(string="Diario de pago")

    x_total_importacion = fields.Float(string="Total importación", digits=(16, 2))

    @api.model
    def _cleanup_old_runs(self, keep=3):
        runs = self.env["penta.import.report.run"].search([], order="create_date desc")
        if len(runs) > keep:
            (runs[keep:]).unlink()

    @classmethod
    def _normalize_key(cls, key):
        key = (key or "").strip().lower()
        return "x_" + key.replace("-", "_").replace(" ", "_")

    def _compute_cell_value(self, pol, f, wiz):
        if f.compute_type == "expr":
            return wiz._eval_expr(pol, f.field_expr)
        m = getattr(wiz, f.method_name, None)
        return m(pol) if m else False

    def _sanitize_value_for_field(self, field, value):
        if value in ("", " ", "null", "None"):
            value = False
        if field.type in ("date", "datetime"):
            return value or False
        if field.type in ("float", "integer", "monetary"):
            if value is False or value is None:
                return False
            if isinstance(value, str):
                try:
                    return float(value) if field.type in ("float", "monetary") else int(float(value))
                except Exception:
                    return False
            return value
        if field.type == "boolean":
            return bool(value)
        if field.type == "many2one":
            if not value:
                return False
            if isinstance(value, int):
                return value
            if hasattr(value, "id"):
                return value.id
            return False
        return value

    @api.model
    def generate_report_for_menu(self):
        AUTO_LIMIT = 500
        BATCH_SIZE = 200

        today = fields.Date.today()
        date_from = today - relativedelta(days=30)
        date_to = today

        pol_obj = self.env["purchase.order.line"]
        domain = [
            ("order_id.id_import.date", ">=", date_from),
            ("order_id.id_import.date", "<=", date_to),
            ("order_id.state", "in", ["purchase", "done"]),
        ]

        total = pol_obj.search_count(domain)
        if total == 0:
            return False
        if total > AUTO_LIMIT:
            return False

        fields_cfg = self.env["penta.import.report.field"].search([("active", "=", True)], order="sequence,id")
        if not fields_cfg:
            return False

        # Limpia runs viejos (no borra todo, borra por cascade)
        self._cleanup_old_runs(keep=3)

        # Crea el RUN
        run = self.env["penta.import.report.run"].create({
            "date_from": date_from,
            "date_to": date_to,
            "total_lines": total,
        })

        pols = pol_obj.search(domain, order="order_id, id")

        wiz = self.env["penta.import.report.wizard"].create({
            "date_from": date_from,
            "date_to": date_to,
        })

        batch = []
        for pol in pols:
            vals = {"purchase_line_id": pol.id, "run_id": run.id}
            for f in fields_cfg:
                field_name = self._normalize_key(f.technical_key)
                if field_name not in self._fields:
                    continue
                raw = self._compute_cell_value(pol, f, wiz)
                vals[field_name] = raw if raw not in ("", " ") else False
            batch.append(vals)

            if len(batch) >= BATCH_SIZE:
                self.create(batch)
                batch = []

        if batch:
            self.create(batch)

        return run.id

class PentaImportReportRun(models.Model):
    _name = "penta.import.report.run"
    _description = "Ejecución Reporte Importaciones"
    _order = "create_date desc"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    total_lines = fields.Integer(string="Total líneas", default=0)