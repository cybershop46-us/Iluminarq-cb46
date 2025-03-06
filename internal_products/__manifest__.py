# -*- coding: utf-8 -*-
{
    'name': "Internal Products",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Cybershop 46",
    'website': "https://cybershop46.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','project','sale_management','stock'],

    # always loaded
    'data': [
        'data/data.xml',
        'views/product.xml',
        'views/project.xml',
        'views/sale_order.xml',
        'views/sale_order_line.xml',

        
    ],
}
