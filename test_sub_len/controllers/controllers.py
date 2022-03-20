# -*- coding: utf-8 -*-
# from odoo import http


# class TestSubLen(http.Controller):
#     @http.route('/test_sub_len/test_sub_len', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/test_sub_len/test_sub_len/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('test_sub_len.listing', {
#             'root': '/test_sub_len/test_sub_len',
#             'objects': http.request.env['test_sub_len.test_sub_len'].search([]),
#         })

#     @http.route('/test_sub_len/test_sub_len/objects/<model("test_sub_len.test_sub_len"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('test_sub_len.object', {
#             'object': obj
#         })
