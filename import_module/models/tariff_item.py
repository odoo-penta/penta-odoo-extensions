from odoo import models, fields

class TariffItem(models.Model):
    _name = 'tariff.item'
    _description = 'Partida Arancelaria'

    code = fields.Char(string='Código', required=True)
    name = fields.Char(string='Nombre', required=True)
    description = fields.Text(string='Descripción')

    line_ids = fields.One2many('tariff.item.line', 'tariff_item_id', string='Líneas')
    
    
    def name_get(self):
        result = []
        print("name rec")
        for rec in self:
            print("name rec")
            # Si solo quieres el código:
            # name = rec.code or ''
            # Si quieres código + descripción:
            name = f"[{rec.code}] {rec.name}" if rec.code else rec.name
            result.append((rec.id, name))
        return result