# -*- coding: utf-8 -*-
{
    'name': 'Productos Tippic Quality Assurance',
    'version': '15.0.1.0.0',
    'summary': 'Personalización para Productos Tippic, modulo de Control de Calidad',
    'description': """
    Este Modulo provee mejoras y funcionalidades para el control y manejo de la calidad en le empresa Productos Tippic.
    """,
    'author': 'DevCios',
    'company': 'Productos Tippic',
    'website': "https://productostippic.com/",
    'maintainer': 'DevCios',
    'category': 'Inventory',
    'depends': ['purchase_stock', 'mrp', 'stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/punto_control_data.xml',
        'data/sequence_data.xml',
        'data/tags_data.xml',
        'views/type.xml',
        'views/tags.xml',
        'views/quality.xml',
        'views/punto_control.xml',
        'views/product_template.xml',
        'views/mrp_production_view.xml',
        'views/menu.xml',
        'views/res_config_settings_views.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True
}
