from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import UserError
REQUIRED_FIELDS_ES = {
    'name': "Nombre",
    'reference': "Referencia",
    'user_id': "Responsable",
    'guide_bl': "Guía de importación",
    'date_shipment': "Fecha estimada de embarque",
    'estimated_time_of_arriva': "Fecha estimada de llegada",
    'real_estimated_time_of_delivery': "Fecha de llegada real",
    'date_of_departure_from_customs': "Fecha de salida de puerto",
    'arrival_date_at_warehouse': "Fecha de llegada al almacén",
    'date_last_delivery_warehouse': "Fecha de última entrega en almacén",
    'supplier_receipt_date': "Fecha recepción proveedor",
    'country': "País de origen",
    'port_of_loading_id': "Puerto de embarque",
    'port_of_discharge_id': "Puerto de llegada",

    'journal_id': "Diario de Pago",
    'payment_method_id': "Método de Pago",
    'payment_reference': "Número de Pago",

    'date': "Fecha guía de importación",
    'dai': "DAI",
    'id_liquidation': "ID Liquidación",
    'date_liquidation': "Fecha de liquidación",
    'date_of_payment': "Fecha de pago de liquidación",
    'freight_agent': "Agente de carga",
    'agent_send_date': "Fecha envío agente",
    'via': "Vía",
    'type_of_load': "Tipo de carga",
    'hazardous_load': "Carga peligrosa",
    'incoterm': "Incoterm",
    'customs_regime_id': "Régimen aduanero",
    'insurance_policy_number': "Número de póliza de seguro",
    'liquidation_value': "Valor de liquidación",
}

class import_module(models.Model):
    _name="x.import" #Nombre de la Base 
    _description="Import"
    _inherit = ['mail.thread', 'mail.activity.mixin']  
    
    name = fields.Char(string="Name", required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')
    sequence_number=fields.Integer()
    record_count = fields.Integer(string='Record Count', compute='_compute_record_count')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('sequence_number')
    def _compute_record_count(self):
        for record in self:
            record.record_count = self.env['x.import'].search_count([])

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals.get('name') in ('New', '/', ''):
            # Compañía del registro (o la actual)
            company = self.env['res.company'].browse(vals.get('company_id')) if vals.get('company_id') else self.env.company

            Seq = self.env['ir.sequence'].sudo()
            seq = Seq.search([('code', '=', 'x.import'), ('company_id', '=', company.id)], limit=1)
            if not seq:
                raise UserError(("No existe la secuencia para Importaciones (code='x.import') en la compañía '%s'. "
                                  "Cree la secuencia primero en Ajustes → Técnico → Secuencias.") % (company.display_name,))

            # Si existe, numerar; si algo falla, avisar
            vals['name'] = Seq.with_company(company).next_by_code('x.import')
            if not vals['name']:
                raise UserError(("No fue posible obtener un número de secuencia (code='x.import') para la compañía '%s'. "
                                  "Revise la configuración de la secuencia.") % (company.display_name,))
        return super().create(vals)
    
    reference = fields.Char(required=True)
    user_id = fields.Many2one("res.users",required=True)
    guide_bl = fields.Char()
    date_shipment = fields.Date(string="Fecha de Envío")
    estimated_time_of_arriva = fields.Date(string="Fecha Estimada de Llegada")
    date_last_delivery_warehouse = fields.Date(string="Fecha de Última Entrega en Almacén")
    date_of_departure_from_customs = fields.Date(string="Fecha de Salida de Aduanas")
    real_estimated_time_of_delivery = fields.Date(string="Fecha Real Estimada de Entrega")
    arrival_date_at_warehouse = fields.Date(string="Fecha de Llegada al Almacén")
    date = fields.Date(string="Fecha")
    country = fields.Many2one("res.country", string="País")
    dai = fields.Char(string="DAI")
    id_liquidation = fields.Char(string="ID de Liquidación")

    @api.model
    def get_system_date(self):
        # Método para obtener la fecha actual del sistema
        return datetime.datetime.now().date()
    
    
    date_liquidation = fields.Date()
    freight_agent=fields.Many2one("res.partner")
    via = fields.Selection(
        [
            ("maritime",'Marítima'),
            ("air","Aérea"),
            ("terrestrial","Terrestre")
        ], 
    )
    type_of_load = fields.Selection(
        [
            ("containerized",'Contenerizada'),
            ("loose cargoe","Carga suelta"),
        ],
    )
    containers_number = fields.Integer(required=True)
    incoterm = fields.Many2one("account.incoterms")
    date_of_payment = fields.Date() #Falta organizar bien


    days_clearance = fields.Integer(string="Days of Clearance", compute="_compute_days_clearance")  
    
    @api.depends('real_estimated_time_of_delivery', 'arrival_date_at_warehouse')
    def _compute_days_clearance(self):
        for record in self:
            if record.real_estimated_time_of_delivery and record.arrival_date_at_warehouse:
                fecha_llegada_real = fields.Date.from_string(record.real_estimated_time_of_delivery)
                fecha_llegada_almacen = fields.Date.from_string(record.arrival_date_at_warehouse)
                record.days_clearance = abs((fecha_llegada_almacen - fecha_llegada_real).days)
            else:
                record.days_clearance = 0

    purchase_ids = fields.One2many("purchase.order","id_import","purchase_ids")
    purchase_order_line_ids = fields.One2many('purchase.order.line', compute="_compute_purchase_order_line_ids",search="_search_purchase_order_line_ids")

    @api.depends('purchase_ids.order_line')
    def _compute_purchase_order_line_ids(self):
        for record in self:
            lines = record.purchase_ids.mapped('order_line')
            record.purchase_order_line_ids = lines.filtered(
                lambda l: l.order_id.state != 'cancel'
            )

    def _search_purchase_order_line_ids(self, operator, value):
        return [('purchase_order_line_ids', operator, value)]

    product_ids = fields.Many2many('product.product', compute="_compute_product_ids")

    @api.depends('purchase_ids.order_line.product_id')
    def _compute_product_ids(self):
        for record in self:
            product_ids = record.purchase_ids.mapped('order_line.product_id')
            record.product_ids = product_ids

    stock_picking_ids = fields.One2many('stock.picking', compute="_compute_stock_picking_ids")
    stock_move_ids = fields.One2many('stock.move', compute="_compute_stock_move_ids")

    @api.depends('purchase_order_line_ids')
    def _compute_stock_picking_ids(self):
        for record in self:
            stock_pickings = self.env['stock.picking'].search([('origin', 'in', record.purchase_order_line_ids.mapped('order_id.name'))])
            record.stock_picking_ids = stock_pickings

    @api.depends('stock_picking_ids')
    def _compute_stock_move_ids(self):
        for record in self:
            moves = self.env['stock.move'].search([
                ('picking_id', 'in', record.stock_picking_ids.ids),
                ('state', '!=', 'cancel'),
            ])
            record.stock_move_ids = moves

    def _get_products_in_picking(self, picking):
        products = picking.move_lines.mapped('product_id')
        return products

    def get_products_in_picking(self):
        products_by_picking = {}
        for picking in self.stock_picking_ids:
            products = self._get_products_in_picking(picking)
            products_by_picking[picking.id] = products
        return products_by_picking
            

    account_move_ids = fields.One2many("account.move", "id_import", "account_move_ids")
    account_move_line_ids = fields.One2many('account.move.line', compute="_compute_account_move_line_ids")
    landed_cost_move_line_ids = fields.One2many('account.move.line', compute="_compute_landed_cost_move_line_ids")

    @api.depends('account_move_ids.line_ids')
    def _compute_account_move_line_ids(self):
        for record in self:
            record.account_move_line_ids = record.account_move_ids.mapped('line_ids')

    @api.depends('account_move_ids.line_ids.product_id')
    def _compute_landed_cost_move_line_ids(self):
        for record in self:
            move_lines = record.account_move_ids.mapped('line_ids')
            landed_cost_lines = move_lines.filtered(
                lambda l: l.product_id.product_tmpl_id.landed_cost_ok
                        and getattr(l.move_id, 'state', 'posted') != 'cancel'
            )
            record.landed_cost_move_line_ids = landed_cost_lines

    stock_landed_cost_ids = fields.One2many("stock.landed.cost", "id_import", "stock_landed_cost_ids")
    stock_landed_cost_line_ids = fields.One2many('stock.landed.cost.lines', compute="_compute_stock_landed_cost_line_ids",search="_search_stock_landed_cost_line_ids")
    @api.depends('stock_landed_cost_ids.cost_lines')
    def _compute_stock_landed_cost_line_ids(self):
        for record in self:
            lines = record.stock_landed_cost_ids.mapped('cost_lines')
            record.stock_landed_cost_line_ids = lines.filtered(
                lambda cl: getattr(cl.cost_id, 'state', 'draft') not in ('cancel', 'cancelled')
            )
    
    def _search_stock_landed_cost_line_ids(self, operator, value):
        return [('stock_landed_cost_line_ids', operator, value)]

    product_ids = fields.Many2many(
        'product.product', 
        compute="_compute_product_ids"
    )

    @api.depends('stock_landed_cost_ids.cost_lines.product_id')
    def _compute_product_ids(self):
        for record in self:
            product_ids = record.stock_landed_cost_ids.mapped('cost_lines.product_id')
            record.product_ids = product_ids



    liquidation_value = fields.Float(string="Liquidation Value", compute="_compute_liquidation_value")

    @api.depends('purchase_order_line_ids.price_subtotal', 'stock_landed_cost_line_ids.price_unit')
    def _compute_liquidation_value(self):
        for record in self:
            purchase_lines = record.purchase_order_line_ids.filtered(
                lambda l: l.order_id.state != 'cancel' and l.price_subtotal
            )
            landed_cost_lines = record.stock_landed_cost_line_ids.filtered(
                lambda cl: getattr(cl.cost_id, 'state', 'draft') not in ('cancel', 'cancelled')
                        and cl.price_unit
            )
            total_purchase_subtotal = sum(purchase_lines.mapped('price_subtotal'))
            total_landed_cost_price_unit = sum(landed_cost_lines.mapped('price_unit'))
            record.liquidation_value = total_purchase_subtotal + total_landed_cost_price_unit

    state = fields.Selection([
        ('new', 'Nuevo'),
        ('process', 'Proceso'),
        ('ready', 'Listo')
    ], default='process')

        
    def _validate_required(self):
        self.ensure_one()
        missing = []
        for fname, label in REQUIRED_FIELDS_ES.items():
            if fname not in self._fields:
                continue
            field = self._fields[fname]
            val = self[fname]
            ftype = field.type

            # Reglas por tipo (detecta M2O correctamente)
            if ftype in ('char', 'text'):
                empty = (val is False or val is None or (isinstance(val, str) and not val.strip()))
            elif ftype == 'many2one':
                empty = not bool(val)          # recordset vacío => False
            elif ftype in ('many2many', 'one2many'):
                empty = len(val) == 0
            elif ftype in ('integer', 'float', 'monetary'):
                empty = (val is False or val is None)  # 0 es válido
            elif ftype in ('date', 'datetime'):
                empty = (val is False or val is None)
            elif ftype == 'boolean':
                empty = False  # se considera “llenado” aunque sea False
            else:
                empty = (val is False or val is None)

            if empty:
                missing.append(label)

        if missing:
            raise UserError("Completa antes de confirmar: " + ", ".join(missing[:12]) + ("…" if len(missing) > 12 else ""))
        
    def change_state(self):
        self.ensure_one()  # Asegura que solo se está operando con un solo registro a la vez
        # Determina el siguiente estado basado en el estado actual
        next_state = {
            'new': 'process',
            'process': 'ready',
            'ready': 'ready'
        }.get(self.state)
          # si vamos a 'ready', valida primero
        if next_state == 'ready':
            self._validate_required()
        self.state = next_state

    button_text = fields.Char(compute='_compute_button_text', string='Texto del Botón')

    @api.depends('state')
    def _compute_button_text(self):
        for record in self:
            if record.state == 'new':
                record.button_text = 'Cambiar estado a process'
            elif record.state == 'process':
                record.button_text = 'Cambiar estado a ready'
            else:
                record.button_text = 'Estado Actual: ready'
                
    def _fields_to_check_for_ready(self):
        """Retorna los nombres de fields a validar (excluye líneas, binarios, computados, readonly duros, etc.)."""
        skip_types = {'one2many', 'many2many', 'binary', 'html'}
        skip_names = {
            'id', 'display_name', 'create_uid', 'create_date', 'write_uid', 'write_date',
            'activity_ids', 'activity_state', 'activity_user_id', 'message_follower_ids',
            'message_ids', 'message_needaction', 'message_partner_ids', 'message_unread',
            'message_has_error', 'message_has_error_counter', 'message_main_attachment_id',
            'state',
        }
        to_check = []
        for name, field in self._fields.items():
            if name in skip_names:
                continue
            if field.type in skip_types:
                continue
            # Omitir campos computados sin inverse (no se pueden escribir por el usuario)
            if getattr(field, 'compute', False) and not getattr(field, 'inverse', False):
                continue
            # Omitir readonly “duro” (sin inverse)
            if field.readonly and not getattr(field, 'inverse', False):
                continue
            to_check.append(name)
        return to_check

    def _validate_all_simple_fields_filled(self):
        """Levanta UserError si encuentra campos vacíos entre los 'simples'."""
        self.ensure_one()
        empty_labels = []
        for fname in self._fields_to_check_for_ready():
            val = self[fname]
            # Considerar vacío: None/False/''
            if val is False or val is None or (isinstance(val, str) and not val.strip()):
                label = self._fields[fname].string or fname
                empty_labels.append(label)
        if empty_labels:
            # Muestra hasta 12 para no hacer el mensaje gigante
            shown = ', '.join(empty_labels[:12])
            suffix = '…' if len(empty_labels) > 12 else ''
            raise UserError(("Completa los siguientes campos antes de confirmar: %s%s") % (shown, suffix))
    
    date_entry_into_inventory=fields.Date(string="Date entry into inventory")
    

    account_move_count=fields.Integer(string="account_move_count", compute="compute_account_move_count")

    def get_account_move_count(self):
        self.ensure_one()
        return{
            'type':'ir.actions.act_window',
            'name':'Prueba',
            'view_mode':'list,form',
            'res_model':'account.move',
            'domain': [
                ('id_import', '=', self.id),
                ('move_type', '=', 'in_invoice'),   # <-- Solo facturas proveedor
            ],
            'context':"{'create':False}"
        }

    def compute_account_move_count(self):
        for record in self:
            record.account_move_count=self.env['account.move'].search_count([('id_import', '=', self.id),('move_type', '=', 'in_invoice')])

    
    purchase_order_count = fields.Integer(string="purchase_order_count", compute="compute_purchase_order_count")

    def compute_purchase_order_count(self):
        for record in self:
            record.purchase_order_count = self.env['purchase.order'].search_count([('id_import', '=', record.id)])

    def get_purchase_order_count(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'purchase_order_count',
            'view_mode': 'list,form',
            'res_model': 'purchase.order',
            'domain': [('id_import', '=', self.id)],
            'context': "{'create': False}"
        }
    
    landed_costs_count = fields.Integer(string="landed_costs_count", compute="compute_landed_costs_count")

    def compute_landed_costs_count(self):
        for record in self:
            record.landed_costs_count = self.env['stock.landed.cost'].search_count([('id_import', '=', record.id)])

    def get_landed_costs_count(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'landed_costs_count',
            'view_mode': 'list,form',
            'res_model': 'stock.landed.cost',
            'domain': [('id_import', '=', self.id)],
            'context': "{'create': False}"
        }
    
    stock_picking_count = fields.Integer(string="stock_move_count", compute="compute_stock_picking_count")

    @api.depends('stock_picking_ids')
    def compute_stock_picking_count(self):
        for record in self:
            # Count the stock pickings associated with the record
            record.stock_picking_count = len(record.stock_picking_ids)

    def get_stock_picking_count(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Encabezado de Stock Picking',
            'view_mode': 'list,form',
            'res_model': 'stock.picking',
            'domain': [('id', 'in', self.stock_picking_ids.ids)],
            'context': "{'create': False}"
        }
    
    transit_time = fields.Integer(string="Tiempo de tránsito", compute="_compute_transit_time")

    @api.depends('date_shipment', 'estimated_time_of_arriva')
    def _compute_transit_time(self):
        for record in self:
            if record.date_shipment and record.estimated_time_of_arriva:
                shipment_date = fields.Date.from_string(record.date_shipment)
                estimated_arrival = fields.Date.from_string(record.estimated_time_of_arriva)
                record.transit_time = abs((estimated_arrival - shipment_date).days)
            else:
                record.transit_time = 0

    customs_regime_id = fields.Many2one('x.customs.regime', string='Régimen Aduanero')
    
    hazardous_load = fields.Selection(
        [
            ('imo', 'IMO'),
            ('no_imo', 'NO IMO')
        ],
        string='Carga peligrosa'
    )
    
    free_days_container_return = fields.Integer(string="Días libres devolución contenedor")
    
    free_days_due_date = fields.Date(string="Fecha de vencimiento días libres", compute="_compute_free_days_due_date")

    @api.depends('real_estimated_time_of_delivery', 'free_days_container_return')
    def _compute_free_days_due_date(self):
        for record in self:
            if record.real_estimated_time_of_delivery and record.free_days_container_return:
                record.free_days_due_date = record.real_estimated_time_of_delivery + timedelta(days=record.free_days_container_return)
            else:
                record.free_days_due_date = False
    
    port_of_loading_id = fields.Many2one(
        'import.boarding',
        string="Puerto de embarque"
    )
    port_of_discharge_id = fields.Many2one(
        'import.boarding',
        string="Puerto de llegada"
    )
    
    insurance_policy_number = fields.Char(string="Número de póliza de seguro")
    virtual_billing = fields.Boolean(string="Facturación virtual")
    supplier_receipt_date = fields.Date(string="Fecha recepción proveedor")

    agent_send_date = fields.Date(string="Fecha envío agente")
    
    payment_count = fields.Integer(string="Pagos", compute="_compute_payment_count")

    def _payments_domain(self):
        """Dominio común para contar y listar pagos relacionados a la importación."""
        self.ensure_one()
        purchase_orders = self.purchase_ids

        # Facturas proveedor que nacen de las OC de esta importación
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('invoice_origin', 'in', purchase_orders.mapped('name')),
        ]).ids

        domain = ['|',
            ('id_import', '=', self.id),           # Pagos ligados directamente a la importación
            ('invoice_ids', 'in', invoices),       # Pagos reconciliados con esas facturas
        ]
        return domain

    @api.depends('purchase_ids')
    def _compute_payment_count(self):
        for record in self:
            count = record.env['account.payment'].search_count(record._payments_domain()) if record.id else 0
            record.payment_count = count

    def _get_related_payments(self):
        self.ensure_one()
        return self.env['account.payment'].search(self._payments_domain())

    def get_related_payments_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pagos relacionados',
            'view_mode': 'list,form',
            'res_model': 'account.payment',
            'domain': self._payments_domain(),
            'context': {'create': False},
        }

    journal_id = fields.Many2one(
        'account.journal',
        string='Diario de Pago',
        domain="[('type', '=', 'bank')]",
        help='Diario desde el cual se realizarán los pagos salientes.',
    )

    payment_method_id = fields.Many2one(
        'account.payment.method.line',
        string='Método de Pago',
        domain="[('payment_type', '=', 'outbound'), ('journal_id', '=', journal_id)]",
        help='Método de pago asociado al diario seleccionado (solo pagos salientes).',
    )

    payment_reference = fields.Char(
        string='Número de Pago',
        help='Número o referencia del pago asociado a la importación.',
    )