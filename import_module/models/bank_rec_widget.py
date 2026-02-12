from odoo import api, fields, models

class BankRecWidgetLine(models.Model):
    _inherit = 'bank.rec.widget.line'

    id_import = fields.Many2one(
        'x.import',
        string='Guía de importación',
        compute='_compute_id_import',
        inverse='_inverse_id_import',
        store=True,
        readonly=False,
        domain="[('state','=','process')]",
    )

    @api.depends('source_aml_id')
    def _compute_id_import(self):
        for line in self:
            if line.flag == 'aml' and line.source_aml_id:
                line.id_import = line.source_aml_id.id_import
    
    def _inverse_id_import(self):
        # Permite que el valor elegido en el widget se conserve
        # No necesitamos lógica extra porque el valor ya está en el record cache
        for line in self:
            line.id_import = line.id_import


    def _get_aml_values(self, **kwargs):
        return super()._get_aml_values(
            **kwargs,
            id_import=self.id_import.id,
        )

class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    def _lines_prepare_tax_line(self, tax_line_vals):
        results = super()._lines_prepare_tax_line(tax_line_vals)
        results['id_import'] = tax_line_vals.get('id_import')
        return results

    def _line_value_changed_id_import(self, line):
        self.ensure_one()
        self._lines_turn_auto_balance_into_manual_line(line)

        if line.flag != 'tax_line':
            self._lines_recompute_taxes()