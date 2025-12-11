# -*- coding: utf-8 -*-
from odoo import models, fields, exceptions, api, _
from odoo.exceptions import ValidationError

class ProcessLineWizard(models.TransientModel):
	_name = "process.line.wizard"
	_description = "Process Line Wizard"

	production_id = fields.Many2one('mrp.production')
	company_id = fields.Many2one('res.company', related="production_id.company_id")
	process_line_ids = fields.One2many('process.order.line', 'manufacture_id')
	product_id = fields.Many2one('product.product', related="production_id.product_id", store=True)
	to_produce_qty = fields.Float(default='1')
	product_qty = fields.Float('Quantity', digits='Product Unit of Measure', related="production_id.product_qty")
	lot_producing_id = fields.Many2one('stock.lot', string='Lot/Serial Number', copy=False, check_company=True, readonly=True)
	qty_producing = fields.Float(string="Quantity Producing", digits='Product Unit of Measure', related="production_id.qty_producing")
	is_produced = fields.Boolean()
	attachment_ids = fields.Many2many('ir.attachment')

	def action_process(self):
		if self.qty_producing < self.product_qty:
			if self.lot_producing_id:
				#self.process_line_ids.mapped('move_id')._action_assign()

				for move in self.production_id.move_finished_ids.filtered(lambda m: m.product_id == self.product_id):
					vals = move._prepare_move_line_vals(quantity=0)
					vals['qty_done'] = 1 if self.product_id.tracking == 'serial' else self.to_produce_qty
					vals['product_uom_id'] = self.product_id.uom_id.id
					vals['lot_id'] = self.lot_producing_id.id
					vals['production_id'] = self.production_id.id
					move_line_id = self.env['stock.move.line'].create(vals)
					for line in self.process_line_ids:
						if line.line_id:
							line.line_id.lot_id = line.lot_id
							line.line_id.qty_done += line.qty_done
							if line.qty_done:
								line.line_id.produce_line_ids = [(4, move_line_id.id)]
						else:
							avl_move = self.production_id.move_raw_ids.filtered(lambda x: x.product_id == line.product_id)
							if avl_move:
								vals = avl_move._prepare_move_line_vals(quantity=0)
								vals['qty_done'] = line.qty_done
								vals['product_uom_id'] = line.product_id.uom_id.id
								vals['lot_id'] = line.lot_id.id
								vals['production_id'] = self.production_id.id
								line_id = self.env['stock.move.line'].create(vals)
								line.line_id = line_id.id
								line_id.produce_line_ids = [(4, move_line_id.id)]

							else:
								mov_vals = self.production_id._get_move_raw_values(line.product_id, line.qty_done, line.product_id.uom_id)
								move_id = self.env['stock.move'].create(mov_vals)
								vals = move_id._prepare_move_line_vals(quantity=0)
								vals['qty_done'] = line.qty_done
								vals['product_uom_id'] = line.product_id.uom_id.id
								vals['lot_id'] = line.lot_id.id
								vals['production_id'] = self.production_id.id
								line_id = self.env['stock.move.line'].create(vals)
								line.line_id = line_id.id
								line_id.produce_line_ids = [(4, move_line_id.id)]

				self.production_id.qty_producing +=  1 if self.product_id.tracking == 'serial' else self.to_produce_qty
				self.lot_producing_id.attachment_ids = self.attachment_ids
			else:
				raise ValidationError(_("Please set Lot/Serial Number."))
		if self.product_qty == self.production_id.qty_producing:
			for production in self.production_id:
				production.write({
					'state': 'to_close',
				})
		return True

	@api.model
	def default_get(self, fields_list):
		vals = super(ProcessLineWizard, self).default_get(fields_list)
		records = []
		active_id = self.env.context.get('active_id')
		prod_id = self.env['mrp.production'].browse(active_id)
		vals['production_id'] = prod_id.id
		to_produce = prod_id.product_qty - prod_id.qty_producing 
		vals['to_produce_qty'] = 1 if prod_id.product_id.tracking == 'serial' else to_produce
		for line in prod_id.move_raw_ids.mapped('move_line_ids'):
			move = line.move_id
			# Total consumido del move
			consumed = sum(move.move_line_ids.mapped("qty_done"))
			# Cantidad pendiente
			uom_qty = move.product_uom_qty - consumed
			if uom_qty <= 0:
				continue
			records.append({
				'line_id': line.id,
				'product_id': line.product_id.id,
				'company_id': line.company_id.id,
				'product_uom_qty': uom_qty,
				'lot_id': line.lot_id.id,
				'qty_done': 0.0,
				'location_id':line.location_id.id,
				'product_uom_id': line.product_uom_id.id
				})
		vals['process_line_ids'] = [(0, 0, rec) for rec in records]
		return vals

	def action_generate_serial(self):
		self.ensure_one()
		self.lot_producing_id = self.env['stock.lot'].create({
			'product_id': self.product_id.id,
			'company_id': self.company_id.id,
			'name': self.env['stock.lot']._get_next_serial(self.company_id, self.product_id) or self.env['ir.sequence'].next_by_code('stock.lot.serial'),
		})
		self.is_produced = True
		return {
			'type': 'ir.actions.act_window',
			'name': "Process Lines",
			'res_model': 'process.line.wizard',
			'target' : 'new',
			'view_mode': 'form',
			'res_id' : self.id,
		}

class ProcessOrderLine(models.TransientModel):
	_name = 'process.order.line'
	_description = 'Process Order Line'

	manufacture_id = fields.Many2one('process.line.wizard')
	line_id = fields.Many2one('stock.move.line', store=True)
	move_id = fields.Many2one('stock.move', related="line_id.move_id", store=True)
	product_id = fields.Many2one('product.product', 'Product', store=True, required=True)
	company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
	product_uom_qty = fields.Float('Reserved', readonly=True)
	qty_done = fields.Float('Done')
	lot_id = fields.Many2one('stock.lot', 'Lot Number')
	location_id = fields.Many2one('stock.location', readonly=True)
	product_uom_id = fields.Many2one('uom.uom', 'Product Unit of Measure')


	@api.onchange('product_id')
	def onchange_product_id(self):
		if self.product_id:
			self.product_uom_id = self.product_id.uom_id.id
