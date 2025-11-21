/** @odoo-module **/

/*
 * Parche único:
 * - Inyecta product_is_ensabled en la línea
 * - Reemplaza computeLineTaxes para evitar que el ICE cambie con descuentos
 */

import { patch } from "@web/core/utils/patch";
import { SaleOrderLine } from "@sale/js/sale_order_line";
import { computeLineTaxes } from "@account/js/account_tax_utils";

// ---------------------------------------------
// 1) EXTENSIÓN: Agregamos product_is_ensabled al frontend
// ---------------------------------------------
patch(SaleOrderLine.prototype, "penta_cb_cluster_motorcycle", {
    setup() {
        this._super();

        // viene en the record.data como product_id -> [id, name]
        // el OWL provee los campos extras en record.data
        this.product_is_ensabled = false;

        try {
            const productData = this.props.record.data;
            if (productData && productData.product_id && productData.product_id.is_ensabled !== undefined) {
                this.product_is_ensabled = productData.product_id.is_ensabled;
            }
        } catch (err) {
            console.warn("PENTA ICE – No se pudo obtener campo is_ensabled en línea", err);
        }
    },
});


// ---------------------------------------------
// 2) PARCHE DEL CÁLCULO PROVISIONAL DE IMPUESTOS
// ---------------------------------------------
const originalComputeLineTaxes = computeLineTaxes;

export function computeLineTaxes(line) {

    const price_unit  = line.price_unit;
    const quantity    = line.quantity || 1;
    const discount    = line.discount || 0;
    const taxes       = line.taxes || [];
    const isEnsam     = line.product_is_ensabled || false;

    // si el producto no es ensamblado → cálculo normal
    if (!isEnsam) {
        return originalComputeLineTaxes(line);
    }

    // reconstruir precio ORIGINAL sin descuento
    let price_original = price_unit;
    if (discount > 0) {
        price_original = price_unit / (1 - (discount / 100));
    }

    // modificar SOLO los impuestos ICE
    const patchedTaxes = taxes.map(tax => {

        if (tax.apply_on_unit_price === true && isEnsam === true) {

            // base corregida sin descuento
            return {
                ...tax,
                base: price_original,
                price_unit: price_original,
            };
        }
        return tax;
    });

    // reinyectamos impuestos modificados
    const patchedLine = {
        ...line,
        taxes: patchedTaxes,
        price_unit: price_unit,  // IVA sí usa price_unit con descuento
    };

    return originalComputeLineTaxes(patchedLine);
}
