# -*- coding: utf-8 -*-
# Part of PentaLab. See LICENSE file for full copyright and licensing details.
# © 2025 PentaLab
# License Odoo Proprietary License v1.0 (https://www.odoo.com/documentation/user/16.0/legal/licenses/licenses.html#odoo-proprietary-license)

import time
from odoo import _, api, models, fields
from odoo.exceptions import UserError
from odoo.tools import local_tz
from datetime import datetime

class ReportProject(models.AbstractModel):
    _name = "report.project.report"
    _description = "Project Report PDF"

    # ============================================================
    # Función principal que obtiene la informacion del proyecto.
    # ============================================================
    def get_project(self, data):
        domain = []

        if data.get('date_start'):
            domain.append(('date_assign', '>=', data['date_start']))
        if data.get('date_end'):
            domain.append(('date_assign', '<=', data['date_end']))

        tasks = self.env['project.task'].search(domain)
        report_lines = []
        
        for task in tasks:
            partner = task.partner_id
            customer_category = ""
            if partner:
                category_ids = (
                    self.env['res.partner.category']
                    .search([('partner_ids', 'in', partner.id)])
                )
                customer_category = ", ".join(category_ids.mapped('name'))
            lot = task.lot_id
            
            chassis = lot.name or ''
            motor_number = lot.motor_number or ''
            placa = lot.plate or ''
            product_name = lot.product_id.name or ''
            internal_referencia_product = lot.product_id.default_code or ''
            model = ''
            if lot.product_id:
                for attr_val in lot.product_id.product_template_attribute_value_ids:
                    if attr_val.attribute_id.name.lower() == 'modelo':
                        model = attr_val.product_attribute_value_id.name or ''
            brand = lot.product_id.product_tmpl_id.product_brand_id.name or ''

            sale_lines_info = self._get_sale_order_line_info(task)
            invoice_info = self._get_invoice_info(task)
            invoice_map = {}
            for inv_line in invoice_info:
                product_id = inv_line.get('product_id')
                if product_id:
                    invoice_map[product_id] = inv_line
            
            for line_info in (sale_lines_info or [{}]): 
                product_id = line_info.get('product_id')
                invoice_line = invoice_map.get(product_id, {})
                effective_date = ''
                dispatch_date= ''
                if task.sale_order_id:
                    pickings = self.env['stock.picking'].search([
                        ('origin', 'in', task.sale_order_id.mapped('name')),
                        ('state', 'in', ['done', 'assigned', 'confirmed']),
                    ], order='date_done desc', limit=1)
                    if pickings:
                        dispatch = pickings.date_done
                        if dispatch:
                            dispatch_local = local_tz(task, dispatch)
                            if isinstance(dispatch_local, str):
                                try:
                                    dispatch_local = datetime.strptime(dispatch_local, "%Y-%m-%d %H:%M:%S")
                                except ValueError:
                                    dispatch_local = datetime.strptime(dispatch_local, "%Y-%m-%d")

                            effective_date = dispatch_local

                            if task.create_date:
                                create_local = local_tz(task, task.create_date)
                                if isinstance(create_local, str):
                                    try:
                                        create_local = datetime.strptime(create_local, "%Y-%m-%d %H:%M:%S")
                                    except ValueError:
                                        create_local = datetime.strptime(create_local, "%Y-%m-%d")

                                dispatch_date_only = dispatch_local.date()
                                create_date_only = create_local.date()
                                difference = (dispatch_date_only - create_date_only).days
                                dispatch_date = difference

                line_data = {
                    'task_id': task.id,
                    'created_on':local_tz(task, task.create_date),
                    'date_assign': local_tz(task, task.date_assign),
                    'effective_date': effective_date.strftime("%Y-%m-%d %H:%M:%S") if effective_date else '',
                    'date_end': local_tz(task, task.date_end),
                    'dispatch_date' : dispatch_date,
                    'effective_hours': task.effective_hours,
                    'stage_id': task.stage_id.name if task.stage_id else '',
                    'user_ids': (
                        ", ".join(task.user_ids.mapped('name')) if task.user_ids else ''
                    ),
                    'under_warranty': task.under_warranty or False,
                    'partner_vat': partner.vat if partner else '',
                    'partner_name': partner.name if partner else '',
                    'customer_category': customer_category,
                    'chassis': chassis,
                    'motor_number': motor_number,
                    'placa': placa,
                    'product_name': product_name,
                    'ref_int_product_name': internal_referencia_product,
                    'model': model,
                    'brand': brand,
                    'line_category': line_info.get('line_category', ''),
                    'product_category': line_info.get('product_category', ''),
                    'product_subcategory': line_info.get('product_subcategory', ''),
                    'internal_reference': line_info.get('internal_reference', ''),
                    'sale_product_name': line_info.get('product_name', ''),
                    'quantity': invoice_line.get('quantity', ''),
                    'unit_price': invoice_line.get('unit_price', ''),
                    'discount':invoice_line.get('discount', ''),
                    'net_amount':invoice_line.get('net_amount', ''),
                    'invoice_status': dict(task._fields['invoice_status'].selection(task)).get(task.invoice_status, ''),
                    'invoice_name': invoice_line.get('invoice_name', ''),
                    'invoice_date': invoice_line.get('invoice_date', ''),
                    'warehouse': invoice_line.get('warehouse', ''),
                    'payment_term': invoice_line.get('payment_term', ''),
                }

                report_lines.append(line_data)
        report_lines.sort(key=lambda x: x.get('task_id', 0))
        return report_lines

    # ================================================================
    # Función que obtiene informacion productos de la orden de venta 
    # ================================================================
    def _get_sale_order_line_info(self, task):
        """Get information from related sales order lines"""
        results = []

        for order in task.sale_order_id:
            for line in order.order_line:
                product = line.product_id
                info = {
                    'product_id': product.id if product else False,
                    'line_category': '',
                    'product_category': '',
                    'product_subcategory': '',
                    'internal_reference': product.default_code or '',
                    'product_name': product.name or '',
                }

                if product.categ_id:
                    categ = product.categ_id
                    if categ.parent_id:
                        info['line_category'] = categ.parent_id.parent_id.name
                        info['product_category'] = categ.parent_id.name
                    else:
                        info['product_category'] = categ.parent_id.name
                    info['product_subcategory'] = categ.name

                results.append(info)

        return results
    # ============================================================
    # Función que obtiene informacion productos de la factura 
    # ============================================================
    def _get_invoice_info(self, task):
        """Obtain information from ALL related invoice lines"""
        results = []

        sale_orders = task.sale_order_id
        if not sale_orders:
            return results
        invoices = self.env['account.move'].search([
            ('invoice_origin', 'in', sale_orders.mapped('name')),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
        ])
        for invoice in invoices:
            invoice_name = invoice.name or ''
            invoice_date = (
            invoice.invoice_date.strftime('%d/%m/%Y')
                if invoice.invoice_date
                else ''
            )
            payment_term = invoice.invoice_payment_term_id.name if invoice.invoice_payment_term_id else ''
            warehouse = sale_orders.warehouse_id.name if sale_orders.warehouse_id else ''

            for line in invoice.invoice_line_ids:
                product = line.product_id
                info = {
                    'product_id': product.id if product else False,
                    'invoice_name': invoice_name,
                    'invoice_date': invoice_date,
                    'payment_term': payment_term,
                    'warehouse': warehouse,
                    'quantity': line.quantity or 0,
                    'unit_price': line.price_unit or 0,
                    'discount': line.discount or 0,
                    'net_amount': line.price_subtotal or 0,
                    'product_name': product.name if product else '',
                    'internal_reference': product.default_code if product else '',
                    'product_category': product.categ_id.name if product and product.categ_id else '',
                }
                results.append(info)

        return results


    # ============================================================
    # Función que envía los datos al reporte QWeb
    # ============================================================
    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get('form'):
            raise UserError(_("There is no data from the form to generate the report."))

        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        docs = self.env[active_model].browse(active_id)
        report_lines = self.get_project(data['form'])

        return {
            'doc_ids': docids,
            'doc_model': active_model,
            'data': data['form'],
            'docs': docs,
            'get_project_lines': report_lines,
            'time': time,
        }
