# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockLot(models.Model):
    _inherit = 'stock.lot'

    motor_number = fields.Char()
    ramv = fields.Char()
    plate = fields.Char(string="Plate",help="Enter the license plate number.")

class ProjectTaskInherit(models.Model):
    _inherit = 'project.task'

    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string="Chassis",
        help="Select the chassis related to this task."
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        related='lot_id.product_id',
        store=True,
        readonly=True
    )


class ProjectReport(models.Model):
    _name = 'project.report'
    _description = 'Project Report Records'
    _order = 'task_id'

    task_internal_id = fields.Integer(related='task_id.id', string='ID', store=True)
    task_id = fields.Many2one('project.task', string='Tarea')
    created_on = fields.Datetime('Create on')
    date_assign = fields.Datetime('Assignment Date')
    effective_date = fields.Datetime('Effective date')
    date_end = fields.Datetime('Completion date')
    dispatch_date = fields.Integer('Length of stay in days')
    effective_hours = fields.Float('Effective Hours')

    stage_id = fields.Char('Work order status')
    user_ids = fields.Char('Mechanic')

    under_warranty = fields.Boolean('Under warranty')

    # Partner
    partner_vat = fields.Char('Identification number')
    partner_name = fields.Char('Customer')
    customer_category = fields.Char('Customer category')

    # Datos vehículo
    chassis = fields.Char('Chassis')
    motor_number = fields.Char('Engine')
    placa = fields.Char('Plate')
    product_name = fields.Char('Product (header)')
    ref_int_product_name = fields.Char('Product (Internal Reference)')
    model = fields.Char('Model')
    brand = fields.Char('Brand')

    # Venta
    line_category = fields.Char('Line (Product category)')
    product_category = fields.Char('Product category')
    product_subcategory = fields.Char('Product subcategory')
    internal_reference = fields.Char('Internal reference')
    sale_product_name = fields.Char('Product (Sales Order)')

    # Factura
    quantity = fields.Float('Quantity')
    unit_price = fields.Float('Unit Price')
    discount = fields.Float('Discount')
    net_amount = fields.Float('Net Amount')
    invoice_status = fields.Char('Invoice Status')
    invoice_name = fields.Char('Invoice')
    invoice_date = fields.Char('Invoice Date')
    warehouse = fields.Char('Almacen')
    payment_term = fields.Char('Tèrmino de pago')

    @api.model
    def load_report(self):
        self.search([]).unlink()

        ReportPDF = self.env['report.project.report']
        data_lines = ReportPDF.get_project({'date_start': False, 'date_end': False})
        
        clean_lines = []
        for line in data_lines:
            clean_line = {}
            for field, value in line.items():
                if value == '':
                    clean_line[field] = False
                    continue

                if isinstance(value, str):
                    try:
                        clean_line[field] = fields.Datetime.to_datetime(value)
                        continue
                    except Exception:
                        pass

                clean_line[field] = value
            clean_lines.append(clean_line)

        for vals in clean_lines:
            self.create(vals)

    @api.model
    def action_load_and_open(self):
        self.load_report()

        # Retornar acción de lista
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lista de Reportes de Proyectos',
            'res_model': 'project.report',
            'view_mode': 'list,pivot',
            'views': [
                (self.env.ref('penta_cb_cluster_motorcycle.view_project_report_list').id, 'list'),
                (self.env.ref('penta_cb_cluster_motorcycle.view_project_report_pivot').id, 'pivot'),
            ],
            'target': 'current',
        }
