from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = "res.partner"

    # TODO: Cambiar bien a computado el campo base city

    city_id = fields.Many2one(
        "res.country.state.city", 
        string="Ciudad",
        domain = "[('state_id', '=', state_id)]",
        )

    city = fields.Char(compute="_compute_city", store=True, invisible=True)

    parroquia_id = fields.Many2one(
        "res.country.state.city.parish", 
        string="Parroquia", 
        domain="[('city_id', '=', city_id)]"
    )

    region_id = fields.Many2one(
        "res.country.state.region", 
        string="Region", 
    )

    @api.onchange("state_id")
    def _onchange_state_id_set_region(self):
        for rec in self:
            rec.city_id = False
            rec.parroquia_id = False

            if rec.state_id:
                rec.region_id = rec.state_id.region_id.id
            else:
                rec.region_id = False

    @api.depends("city_id")
    def _compute_city(self):
        for rec in self:
            rec.city = rec.city_id.name if rec.city_id else ""