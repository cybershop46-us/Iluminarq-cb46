# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    internal_product_ids = fields.One2many(comodel_name='sale.order.line',
                                           inverse_name='project_id' ,
                                             string="Internal Products", store=True)

    def action_view_internal_products(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Internal Products',
            'res_model': 'sale.order.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.internal_product_ids.ids)],
            'target': 'current',
        }