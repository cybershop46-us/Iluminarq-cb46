# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_internal_product = fields.Boolean('Internal Product', help="Indicates if the product is an internal product not invoiced.")