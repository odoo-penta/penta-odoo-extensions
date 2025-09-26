-- FLAT: una fila por documento (Factura/NC o Recepción) para cada línea de OC
DROP FUNCTION IF EXISTS l10n_ec_penta_base_get_purchase_report_flat(date,date,integer);

CREATE OR REPLACE FUNCTION l10n_ec_penta_base_get_purchase_report_flat(
    p_date_from date,
    p_date_to   date,
    p_product_id integer DEFAULT NULL
)
RETURNS TABLE (
    -- Contexto línea OC (idéntico por cada fila-doc)
    po_name text,
    po_date_approve date,
    supplier text,
    product_default_code text,
    product_name text,
    po_create_date date,
    po_request_date date,
    qty_ordered numeric,
    qty_received_total numeric,
    po_amount numeric,
    invoice_amount_total numeric,
    diff_units numeric,
    diff_amount numeric,
    -- Detalle del documento (varía por fila)
    doc_type text,         -- 'Factura', 'Nota de crédito', 'Recepción'
    doc_name text,         -- número factura/NC o nombre del albarán
    doc_date date,         -- fecha factura/NC o fecha efectiva recepción
    doc_qty numeric,       -- qty en la línea de factura o qty recibida en el move
    doc_amount numeric     -- subtotal factura (NC negativo) o qty_rec * price_unit_OC
) AS
$$
WITH pol AS (
    SELECT
        l.id                           AS pol_id,
        o.id                           AS po_id,
        o.name                         AS po_name,
        o.date_approve::date           AS po_date_approve,
        o.create_date::date            AS po_create_date,
        o.partner_id                   AS partner_id,
        COALESCE(l.date_planned::date, o.date_planned::date) AS po_request_date,
        l.product_id                   AS product_id,
        l.product_qty                  AS qty_ordered,
        l.price_unit                   AS po_price_unit,
        o.id_import                    AS import_id
    FROM purchase_order_line l
    JOIN purchase_order o ON o.id = l.order_id
    WHERE o.state IN ('purchase','done')
      AND o.date_approve::date BETWEEN p_date_from AND p_date_to
      AND (p_product_id IS NULL OR l.product_id = p_product_id)
),
recv_total AS (
    SELECT
        m.purchase_line_id AS pol_id,
        SUM(m.quantity_done) AS qty_received_total
    FROM stock_move m
    WHERE m.state='done' AND m.purchase_line_id IS NOT NULL
    GROUP BY m.purchase_line_id
),
inv_total AS (
    SELECT
        aml.purchase_line_id AS pol_id,
        SUM( (CASE WHEN am.move_type='in_refund' THEN -1 ELSE 1 END) * aml.price_subtotal ) AS invoice_amount_total
    FROM account_move_line aml
    JOIN account_move am ON am.id = aml.move_id
    WHERE aml.purchase_line_id IS NOT NULL
      AND aml.display_type IS NULL
      AND am.state='posted'
      AND am.move_type IN ('in_invoice','in_refund')
    GROUP BY aml.purchase_line_id
),
imp AS (
    SELECT i.id AS import_id, i.name AS import_name FROM x_import i
),
prod AS (
    SELECT p.id AS product_id, p.default_code, pt.name
    FROM product_product p JOIN product_template pt ON pt.id = p.product_tmpl_id
),
sup AS (
    SELECT rp.id AS partner_id, COALESCE(rp.display_name, rp.name) AS supplier
    FROM res_partner rp
),
-- Detalle de facturas y NC (una fila por línea de factura ligada a la línea OC)
inv_rows AS (
    SELECT
        pol.pol_id,
        CASE WHEN am.move_type='in_refund' THEN 'Nota de crédito' ELSE 'Factura' END AS doc_type,
        am.name      AS doc_name,
        am.invoice_date::date AS doc_date,
        aml.quantity AS doc_qty,
        (CASE WHEN am.move_type='in_refund' THEN -aml.price_subtotal ELSE aml.price_subtotal END) AS doc_amount
    FROM pol
    JOIN account_move_line aml ON aml.purchase_line_id = pol.pol_id
    JOIN account_move am ON am.id = aml.move_id
    WHERE aml.display_type IS NULL
      AND am.state='posted'
      AND am.move_type IN ('in_invoice','in_refund')
),
-- Detalle de recepciones (una fila por move hecho ligado a la línea OC)
rec_rows AS (
    SELECT
        pol.pol_id,
        'Recepción' AS doc_type,
        p.name      AS doc_name,
        COALESCE(p.date_done::date, p.scheduled_date::date, m.date::date) AS doc_date,
        m.quantity_done AS doc_qty,
        (m.quantity_done * pol.po_price_unit) AS doc_amount
    FROM pol
    JOIN stock_move m ON m.purchase_line_id = pol.pol_id
    LEFT JOIN stock_picking p ON p.id = m.picking_id
    WHERE m.state='done'
),
all_docs AS (
    SELECT * FROM inv_rows
    UNION ALL
    SELECT * FROM rec_rows
)
SELECT
    -- OC (concatena importación si existe)
    CASE WHEN pol.import_id IS NOT NULL AND imp.import_name IS NOT NULL
         THEN pol.po_name || ' / ' || imp.import_name
         ELSE pol.po_name
    END AS po_name,
    pol.po_date_approve,
    sup.supplier,
    prod.default_code AS product_default_code,
    prod.name         AS product_name,
    pol.po_create_date,
    pol.po_request_date,
    COALESCE(pol.qty_ordered,0) AS qty_ordered,
    COALESCE(rt.qty_received_total,0) AS qty_received_total,
    (COALESCE(pol.qty_ordered,0) * COALESCE(pol.po_price_unit,0)) AS po_amount,
    COALESCE(it.invoice_amount_total,0) AS invoice_amount_total,
    COALESCE(pol.qty_ordered,0) - COALESCE(rt.qty_received_total,0) AS diff_units,
    COALESCE(it.invoice_amount_total,0) - (COALESCE(rt.qty_received_total,0) * COALESCE(pol.po_price_unit,0)) AS diff_amount,
    -- Documento puntual (fila)
    d.doc_type,
    d.doc_name,
    d.doc_date,
    COALESCE(d.doc_qty,0) AS doc_qty,
    COALESCE(d.doc_amount,0) AS doc_amount
FROM all_docs d
JOIN pol           ON pol.pol_id = d.pol_id
LEFT JOIN recv_total rt ON rt.pol_id = pol.pol_id
LEFT JOIN inv_total it  ON it.pol_id = pol.pol_id
LEFT JOIN imp           ON imp.import_id = pol.import_id
LEFT JOIN prod          ON prod.product_id = pol.product_id
LEFT JOIN sup           ON sup.partner_id  = pol.partner_id
ORDER BY pol.po_id, pol.pol_id, d.doc_date NULLS LAST, d.doc_type, d.doc_name;
$$ LANGUAGE sql STABLE;
