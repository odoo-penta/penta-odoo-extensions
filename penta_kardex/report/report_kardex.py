# -*- coding: utf-8 -*-
# Part of PentaLab. See LICENSE file for full copyright and licensing details.
# © 2025 PentaLab
# License Odoo Proprietary License v1.0 (https://www.odoo.com/documentation/user/16.0/legal/licenses/licenses.html#odoo-proprietary-license)

import time
from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import float_round

class ReportKardex(models.AbstractModel):
    _name = "report.penta_kardex.kardex_report"
    _description = "Reporte Kardex PDF"

    # ============================================================
    # Función principal que obtiene las líneas del Kardex
    # ============================================================
    def get_kardex(self, data):
        """Devuelve las líneas del Kardex entre las fechas y producto seleccionado usando stock.valuation.layer"""

        date_start = data.get("date_start")
        date_end = data.get("date_end")
        product_id = data.get("product_id")
        warehouse_id = data.get("warehouse_id")
        location_id = data.get("location_id")

        if not date_start or not date_end or not product_id:
            raise UserError(_("Por favor, selecciona la fecha de inicio, fin y el producto."))

        product = self.env["product.template"].browse(product_id[0])

        # ============================================================
        # Precisión decimal definida para precios
        # ============================================================
        price_precision = self.env['decimal.precision'].precision_get('Product Price')

        # ============================================================
        # Movimientos de stock del producto en las fechas
        # ============================================================
        domain = [
            ("date", ">=", date_start),
            ("date", "<=", date_end),
            ("product_id.product_tmpl_id", "=", product.id),
            ("state", "=", "done"),
        ]

        # Solo filtramos por ubicación si el usuario seleccionó una
        if location_id:
            domain.append(("location_id", "=", location_id[0]))

        # Solo filtramos por almacén si el usuario seleccionó uno
        if warehouse_id:
            domain.append(("picking_type_id.warehouse_id", "=", warehouse_id[0]))

        stock_moves = self.env["stock.move"].search(domain, order="date asc")

        # ============================================================
        # Capas de valoración
        # ============================================================
        val_layers = self.env["stock.valuation.layer"].search([
            ("product_id.product_tmpl_id", "=", product.id),
            ("create_date", ">=", date_start),
            ("create_date", "<=", date_end),
        ])

        lines = []
        qty_balance = 0.0
        cost_avg = 0.0
        credit_note = ""

        for move in stock_moves:

            move_type = move.picking_type_id.code or "adjust"

            # Obtener valuation layers del movimiento
            layers = val_layers.filtered(lambda l: l.stock_move_id.id == move.id)

            total_in = total_out = 0.0
            # Costos unitarios de valuation (antes de factura)
            cost_in_unit = cost_out_unit = 0.0

            # ============================================================
            # Determinar entradas/salidas según valuation layers
            # ============================================================
            for layer in layers:
                if layer.quantity > 0:
                    total_in += layer.quantity
                    cost_in_unit = layer.unit_cost  # unit_cost del layer exacto
                elif layer.quantity < 0:
                    total_out += abs(layer.quantity)
                    cost_out_unit = layer.unit_cost

            # ============================================================
            # Aplicar reglas de entrada/salida según tipo de movimiento
            # ============================================================
            if move_type == "incoming":
                qty_in = total_in
                qty_out = 0.0
            elif move_type == "outgoing":
                qty_in = 0.0
                qty_out = total_out
            elif move_type == "internal":
                qty_in = total_in
                qty_out = total_out
            else:
                # Ajustes
                if total_in > 0:
                    qty_in = total_in
                    qty_out = 0.0
                elif total_out > 0:
                    qty_in = 0.0
                    qty_out = total_out
                else:
                    qty_in = qty_out = 0.0

            # ============================================================
            # Reemplazar costo unitario por costo de factura (si existe)
            # ============================================================
            if move_type == "incoming" and qty_in > 0:

                # Buscar purchase.order desde el picking
                purchase_order = False
                sale_order = False
                if move.picking_id and move.picking_id.origin:
                    purchase_order = self.env["purchase.order"].search(
                        [("name", "=", move.picking_id.origin)],
                        limit=1
                    )

                if purchase_order:
                    # Buscar factura posteada asociada
                    invoice = purchase_order.invoice_ids.filtered(lambda inv: inv.state == "posted" and inv.move_type == "in_invoice")

                    if invoice:
                        # Buscar la línea de factura del producto
                        inv_line = invoice.mapped("invoice_line_ids").filtered(
                            lambda l: l.product_id.id == move.product_id.id
                        )
                        if inv_line:
                            cost_in_unit = inv_line[0].price_unit

                # Buscar sale.order desde el picking
                matches = []   # lista donde guardar relacion devolución <-> nota de crédito

                if move.picking_id and move.picking_id.return_id and move.picking_id.return_id.origin:

                    sale_order = self.env["sale.order"].search(
                        [("name", "=", move.picking_id.return_id.origin)],
                        limit=1
                    )

                    qty_return = move.quantity  # cantidad devuelta

                if sale_order:
                    # Buscar factura posteada asociada
                    credit_notes = sale_order.invoice_ids.filtered(lambda inv: inv.state == "posted" and inv.move_type == "out_refund")

                    for credit in credit_notes:
                        # Filtrar líneas del producto de esa nota de crédito
                        credit_line = credit.invoice_line_ids.filtered(
                            lambda l: l.product_id.id == move.product_id.id
                        )

                        if not credit_line:
                            continue

                        # Cantidad de la línea de nota de crédito
                        qty_credit = credit_line[0].quantity

                        # 4. MATCH EXACTO
                        if qty_credit == qty_return and credit not in [m['credit'] for m in matches]:
                            cost_in_unit = credit_line[0].price_unit
                            credit_note = credit.name
                            break 

            if move_type == "outgoing" and qty_out > 0:
                sale_order = False
                purchase_order = False
                if move.picking_id and move.picking_id.origin:
                    sale_order = self.env['sale.order'].search([('name', '=', move.picking_id.origin)], limit=1)

                    if sale_order:
                        # Buscar factura posteada asociada
                        invoice = sale_order.invoice_ids.filtered(lambda inv: inv.state == "posted" and inv.move_type == "out_invoice")

                        if invoice:
                            invoice_line = invoice.mapped("invoice_line_ids").filtered(
                                lambda l: l.product_id.id == move.product_id.id
                            )
                            if invoice_line:
                                cost_out_unit = invoice_line[0].price_unit
                matches = []   # lista donde guardar relacion devolución <-> nota de crédito
                if move.picking_id and move.picking_id.return_id and move.picking_id.return_id.origin:
                    purchase_order = self.env['purchase.order'].search([('name', '=', move.picking_id.return_id.origin)], limit=1)

                    qty_return = move.quantity
                    if purchase_order:
                        credit_notes = purchase_order.invoice_ids.filtered(lambda inv: inv.state == "posted" and inv.move_type == "in_refund")
                        for credit in credit_notes:
                            credit_line = credit.invoice_line_ids.filtered(
                                lambda l: l.product_id.id == move.product_id.id
                            )
                            if not credit_line:
                                continue
                            
                            qty_credit = credit_line[0].quantity

                            if qty_credit == qty_return and credit not in [m['credit'] for m in matches]:
                                cost_out_unit = credit_line[0].price_unit
                                credit_note = credit.name
                                break
                        
            # ============================================================
            # Cálculo de totales sin redondeos
            # ============================================================
            cost_in_total = cost_in_unit * qty_in
            cost_out_total = cost_out_unit * qty_out

            # ============================================================
            # Actualizar saldos
            # ============================================================
            prev_balance = qty_balance
            qty_balance += qty_in - qty_out

            # Si hay existencia, recalcular costo promedio
            if qty_balance > 0:
                # costo promedio: (stock anterior + ingreso - egreso) / balance
                cost_avg = ((cost_avg * prev_balance) + cost_in_total - cost_out_total) / qty_balance

            cost_total_balance = cost_avg * qty_balance

            # ============================================================
            # Determinar tipo de movimiento (etiqueta)
            # ============================================================
            type_translations = {
                "incoming": "Entrada",
                "outgoing": "Salida",
                "internal": "Transferencia interna",
                "adjust": "Ajuste de inventario",
            }

            type_dict = dict(move.picking_type_id._fields["code"].selection)
            move_type_label = type_translations.get(move_type, type_dict.get(move_type, "Sin tipo"))

            # ============================================================
            # Buscar factura asociada solo para mostrar
            # ============================================================
            invoice_name = ""
            picking = move.picking_id
            if picking and picking.origin:
                sale = self.env["sale.order"].search([("name", "=", picking.origin)], limit=1)
                purchase = self.env["purchase.order"].search([("name", "=", picking.origin)], limit=1)

                if sale:
                    invoice_name = ", ".join(
                        sale.invoice_ids.filtered(lambda inv: inv.state == "posted" and inv.move_type == "out_invoice").mapped("name")
                    )
                elif purchase:
                    invoice_name = ", ".join(
                        purchase.invoice_ids.filtered(lambda inv: inv.state == "posted" and inv.move_type == "in_invoice").mapped("name")
                    )
                elif credit_note:
                    invoice_name = credit_note

            # ============================================================
            # Agregar línea final
            # ============================================================
            lines.append({
                "date": move.date.strftime("%Y-%m-%d"),
                "type": move_type_label,
                "reference": move.reference or "",
                "voucher": invoice_name or "",
                "qty_in": qty_in,
                "cost_in_unit": float_round(cost_in_unit, precision_digits=price_precision),
                "cost_in_total": float_round(cost_in_total, precision_digits=price_precision),
                "qty_out": qty_out,
                "cost_out_unit": float_round(cost_out_unit, precision_digits=price_precision),
                "cost_out_total": float_round(cost_out_total, precision_digits=price_precision),
                "qty_balance": qty_balance,
                "cost_avg_unit": float_round(cost_avg, precision_digits=price_precision),
                "cost_total_balance": float_round(cost_total_balance, precision_digits=price_precision),
            })

        return lines

    # ============================================================
    # Función que envía los datos al reporte QWeb
    # ============================================================
    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get("form"):
            raise UserError(_("No hay datos del formulario para generar el reporte."))

        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")

        docs = self.env[active_model].browse(active_id)
        report_lines = self.get_kardex(data["form"])

        return {
            "doc_ids": docids,
            "doc_model": active_model,
            "data": data["form"],
            "docs": docs,
            "get_kardex_lines": report_lines,
            "time": time,
        }