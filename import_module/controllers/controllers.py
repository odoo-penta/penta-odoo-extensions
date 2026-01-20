# -*- coding: utf-8 -*-
# from odoo import http


# class ImportModule(http.Controller):
#     @http.route('/import_module/import_module', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/import_module/import_module/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('import_module.listing', {
#             'root': '/import_module/import_module',
#             'objects': http.request.env['import_module.import_module'].search([]),
#         })

#     @http.route('/import_module/import_module/objects/<model("import_module.import_module"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('import_module.object', {
#             'object': obj
#         })
