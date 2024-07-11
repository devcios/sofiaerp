# -*- coding: utf-8 -*-
{
    'name': 'Inventory Adjustment Screen App',
    'author': "Edge Technologies",
    'version': '15.0.1.0',
    'live_test_url':'https://youtu.be/MlSyDrDb3Lk',
    "images": ['static/description/main_screenshot.png'],
    'summary' : 'Show Inventory Adjustment Screen update stock via Inventory Adjustment Screen Inventory Adjustment menu Inventory Adjustment view show Inventory Adjustment view show Inventory Adjustment Screen menu',
    'description': """
        This app helps to we will be able to type wise inventory adjustment like all product, one category, one lot/serial number, one product and also select a manual product.
    """,
    "license": "OPL-1",
    'depends': ['base', 'stock'],
    'data': [
            'security/ir.model.access.csv',
            'views/stock_inventory_view.xml',
            'report/inventory_report.xml',
            ],
    'demo' : [],
    'installable': True,
    'auto_install': False,
    'price': 22,
    'currency': "EUR",
    'category' : 'Warehouse',
}
