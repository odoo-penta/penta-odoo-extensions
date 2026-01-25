from odoo import models, fields, api
import datetime
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round


class stock_landed_cost_module(models.Model):
    _inherit="stock.landed.cost"
    
    id_import = fields.Many2one(
        "x.import",
        string="Importación",
        domain="[('state', '=', 'process')]"
    )

    tax_lines = fields.One2many(
        'stock.landed.cost.taxes',
        'landed_cost_id',
        string='Líneas de Impuesto'
    )

    def action_backfill_move_import_ids(self):
        """Rellena id_import en moves existentes a partir de liquidaciones."""
        for lc in self.search([('id_import', '!=', False)]):
            lc._propagate_import_to_move()
        
    def _propagate_import_to_move(self):
        """Escribe id_import en el move contable asociado a la liquidación.
        Fallback: si no hay account_move_id, busca por ref == name de la liquidación.
        """
        Move = self.env['account.move'].sudo()
        for rec in self:
            if not rec.id_import:
                continue

            move = rec.account_move_id
            if not move:
                # Fallback por ref (cuando el asiento existe pero no está enlazado)
                move = Move.search([('ref', '=', rec.name)], limit=1)

            if move and move.id_import != rec.id_import:
                move.write({'id_import': rec.id_import.id})

    def button_validate(self):
        res = super().button_validate()
        self._propagate_import_to_move()
        return res

    def write(self, vals):
        res = super().write(vals)
        # Si cambió la importación o se enlazó el move, volvemos a propagar
        if any(k in vals for k in ('id_import', 'account_move_id', 'name')):
            self._propagate_import_to_move()
        return res
    
    
    def action_calcular_impuesto(self):
        self.ensure_one()

        # -------- Validar que existan flete y seguro en cost_lines
        freight_lines = self.cost_lines.filtered(lambda cl: cl.product_id and cl.product_id.landed_cost_type == 'freight')
        insurance_lines = self.cost_lines.filtered(lambda cl: cl.product_id and cl.product_id.landed_cost_type == 'insurance')
        if not freight_lines or not insurance_lines:
            raise UserError("Faltan líneas de costo requeridas: asegúrate de tener al menos un producto con (Flete) y uno con (Seguro).")

        freight_total = sum(f.price_unit for f in freight_lines)
        insurance_total = sum(s.price_unit for s in insurance_lines)

        # -------- Filtrar valuation_adjustment_lines por productos customs (del cost_line)
        adjs = self.valuation_adjustment_lines.filtered(
            lambda l: l.cost_line_id
            and l.cost_line_id.product_id
            and l.cost_line_id.product_id.product_tmpl_id.landed_cost_type == 'customs'
        )
        if not adjs:
            raise UserError("No hay líneas de valoración con productos de tipo 'Costo de Aduana'.")

        # -------- Obtener lista SRI
        sri_pricelist = self.env['product.pricelist'].search([('sri_list_price', '=', True)], limit=1)
        if not sri_pricelist:
            raise UserError("No existe una lista de precios marcada como 'Lista SRI'.")

        # -------- Reiniciar líneas de impuestos para evitar duplicados
        if hasattr(self, 'tax_lines') and self.tax_lines:
            self.tax_lines.unlink()

        TaxLine = self.env['stock.landed.cost.taxes']
        TariffItemLine = self.env['tariff.item.line']
        ref_date = fields.Date.context_today(self)

        skipped = []  # ⬅️ NUEVO: para informar productos saltados por no estar en la partida

        for l in adjs:
            prod_cost = l.cost_line_id.product_id      # producto del cost_line (customs)
            prod_move = l.product_id                    # producto recepcionado (va en taxes.product_id)

            # Partida arancelaria del producto recepcionado
            recv_tariff_item = getattr(prod_move.product_tmpl_id, 'tariff_item_id', False)

            # Validar que la partida contemple ESTE producto de costo
            til = TariffItemLine.search([
                ('tariff_item_id', '=', recv_tariff_item.id if recv_tariff_item else False),
                ('product_id', '=', prod_cost.id),
                ('date_from', '<=', ref_date),
            ], order='date_from desc, id desc', limit=1)

            if not til:
                skipped.append(prod_move.display_name)
                continue

            percentage = til.percentage or 0.0

            # --- NUEVO: tomar flete/seguro de las líneas VAL "hermanas" (1:1)
            siblings = self.valuation_adjustment_lines.filtered(
                lambda r: r.move_id == l.move_id
            )
            freight_adjs = siblings.filtered(
                lambda r: r.cost_line_id
                and r.cost_line_id.product_id
                and r.cost_line_id.product_id.product_tmpl_id.landed_cost_type == 'freight'
            )
            insurance_adjs = siblings.filtered(
                lambda r: r.cost_line_id
                and r.cost_line_id.product_id
                and r.cost_line_id.product_id.product_tmpl_id.landed_cost_type == 'insurance'
            )

            freight_share = sum(fa.additional_landed_cost for fa in freight_adjs) if freight_adjs else 0.0
            insurance_share = sum(ia.additional_landed_cost for ia in insurance_adjs) if insurance_adjs else 0.0

            # CIF usando la suma total de flete y seguro
            cif = l.former_cost + freight_share + insurance_share
            # ¿Producto con ICE?
           
            prod_cost_tmpl = l.cost_line_id.product_id.product_tmpl_id
            is_ice = (getattr(prod_cost_tmpl, 'type_classification', False) == 'ice')
            
            if is_ice:
                pvp = self._get_fixed_price_from_pricelist(sri_pricelist, prod_move)
                tax_value = pvp * 0.05                 # ICE
            else:
                tax_value = cif * (percentage / 100.0) # Ad-Valorem / FODINFA (vía porcentaje)
    
            TaxLine.create({
                'landed_cost_id': self.id,
                'product_id': prod_move.id,
                'cost_line': prod_cost.display_name,
                'quantity': l.quantity,
                'tariff_item_id': til.tariff_item_id.id,
                'value_original_unit': l.former_cost,
                'cif': cif,
                'percentage': percentage,
                'tax_value': tax_value,
                'val_line_id': l.id,
                'cost_product_id': prod_cost.id
            })
            
        # ⬅️ NUEVO: feedback opcional (no bloquea)
        if skipped:
            # Puedes convertirlo en warning log o mail.message, según prefieras
            _logger.info("Productos sin línea de impuesto por no estar en la partida: %s", ", ".join(set(skipped)))

        return True

    def action_push_tax_to_original_lines(self):
        self.ensure_one()
        print("\n=========== [DEBUG] INICIO: action_push_tax_to_original_lines ===========")

        if self.state != 'draft':
            print("[STOP] Estado no es 'draft':", self.state)
            raise UserError(("Solo puedes aplicar impuestos en estado Borrador."))

        if not self.tax_lines:
            print("[STOP] No existen tax_lines.")
            raise UserError(("No hay líneas de impuestos calculadas."))

        # Validación estricta: TODAS con enlace VAL
        missing = self.tax_lines.filtered(lambda tl: not tl.val_line_id)
        if missing:
            print("[STOP] Líneas sin val_line_id:", missing.ids)
            raise UserError(_("Existen líneas de impuestos sin 'VAL origen' (val_line_id). Corrige antes de continuar."))

        currency = self.company_id.currency_id
        precision = currency.rounding
        print(f"[INFO] Moneda: {currency.name}, redondeo: {precision}")

        # Agrupar por producto de costo (p. ej., "FODINFA 1", "FODINFA 2", etc.)
        groups = {}
        for tl in self.tax_lines:
            key = tl.cost_product_id.id
            groups.setdefault(key, []).append(tl)

        print(f"[INFO] Se encontraron {len(groups)} grupos de productos de costo.")

        for prod_id, tls in groups.items():
            tls = self.env['stock.landed.cost.taxes'].browse([t.id for t in tls])
            prod_name = tls[0].cost_product_id.display_name if tls and tls[0].cost_product_id else "N/A"
            print("\n--- Grupo producto de costo:", prod_name, f"({prod_id}) ---")

            # Totales
            total_calc = sum(tls.mapped('tax_value')) or 0.0
            cl_total = abs(sum(self.cost_lines.filtered(
                lambda cl: cl.product_id and cl.product_id.id == prod_id
            ).mapped('price_unit')) or 0.0)

            delta = cl_total - total_calc
            print(f"[DEBUG] total_calc={total_calc:.4f} | cl_total(abs)={cl_total:.4f} | delta={delta:.4f}")

            # Si no hay descuadre relevante, solo aplicar tal cual
            if abs(delta) < 0.01:
                print(f"[INFO] Delta {delta:.4f} menor a 0.01 USD, no se recalcula (copia directa).")
                for tl in tls:
                    tl.val_line_id.write({'additional_landed_cost': float_round(tl.tax_value, precision_rounding=precision)})
                self.env.cr.flush()
                continue

            # Reparto proporcional del delta según el peso de cada línea
            if total_calc == 0.0:
                raise UserError(_("No se puede ajustar el producto de costo '%s' porque el total calculado es 0 y cost_lines suman %.2f.")
                                % (prod_name, cl_total))

            # Calcular pesos y ajustes redondeados
            weights = {tl.id: (tl.tax_value / total_calc) for tl in tls}
            adjusted_vals = {}
            sum_adjusted = 0.0

            print("[DEBUG] Pesos por línea:")
            for tl in tls:
                print(f"  - VAL {tl.val_line_id.id} ({tl.product_id.display_name}): peso={weights[tl.id]:.6f}, tax_value={tl.tax_value:.4f}")

            # Asignar ajustes iniciales (redondeados)
            for tl in tls:
                adj = float_round(delta * weights[tl.id], precision_rounding=precision)
                new_val = float_round(tl.tax_value + adj, precision_rounding=precision)
                adjusted_vals[tl.id] = new_val
                sum_adjusted += new_val
                print(f"  -> Ajuste inicial VAL {tl.val_line_id.id}: adj={adj:.4f}, new_val={new_val:.4f}")

            # Calcular residuo (por redondeo)
            residuo = float_round(cl_total - sum_adjusted, precision_rounding=precision)
            print(f"[DEBUG] Suma ajustada={sum_adjusted:.4f}, residuo final={residuo:.4f}")

            if abs(residuo) > 0:
                # Asignar residuo a la línea con MAYOR peso (mayor tax_value)
                biggest = max(tls, key=lambda t: t.tax_value)
                adjusted_vals[biggest.id] = float_round(adjusted_vals[biggest.id] + residuo, precision_rounding=precision)
                print(f"[INFO] Residuo {residuo:.4f} aplicado a la VAL {biggest.val_line_id.id} ({biggest.product_id.display_name}).")

            # Escribir los valores finales en las VAL originales
            for tl in tls:
                final_val = adjusted_vals[tl.id]
                print(f"[WRITE] VAL {tl.val_line_id.id} => additional_landed_cost={final_val:.4f}")
                tl.val_line_id.write({'additional_landed_cost': final_val})

        print("=========== [DEBUG] FIN: action_push_tax_to_original_lines ===========\n")
        return True

    
    def _get_fixed_price_from_pricelist(self, pricelist, product):
        """
        Devuelve el precio FIJO configurado directamente para la variante 'product'
        en la lista de precios 'pricelist'. Si no existe, lanza error.
        """
        self.ensure_one()
        if not pricelist:
            raise UserError("No se especificó lista de precios.")
        if not product:
            raise UserError("No se especificó el producto para obtener el precio.")

        item = self.env['product.pricelist.item'].search([
            ('pricelist_id', '=', pricelist.id),
            ('applied_on', '=', '1_product'),
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
            ('compute_price', '=', 'fixed'),
        ], order='id desc', limit=1)

        if not item:
            raise UserError(
                f"No existe precio fijo en la lista '{pricelist.display_name}' "
                f"para el producto '{product.display_name}'."
            )
        if item.fixed_price in (None, False):
            raise UserError(
                f"El precio fijo no está configurado en la lista '{pricelist.display_name}' "
                f"para '{product.display_name}'."
            )
        return item.fixed_price
    
    def action_open_taxes_io_wizard(self):
            self.ensure_one()
            return {
                'type': 'ir.actions.act_window',
                'name': 'Exportar Impuestos',
                'res_model': 'lc.taxes.io.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'active_id': self.id},
            }

class StockLandedCostLines(models.Model):
    _inherit = 'stock.landed.cost.lines'

    account_move_id = fields.Many2one(
        'account.move',
        string='Factura Proveedor',
        readonly=True,
        domain="[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]",
        index=True
    )

