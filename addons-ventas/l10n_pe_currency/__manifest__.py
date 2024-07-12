# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C)  2024.
#    Author      :  Sofia ERP (<http://www.sofiaerp.com>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

{
    'name': 'Modulo de Tipo de cambio del día - Perú',
    'version': '15.0.1.0',
    'author': 'Sofia ERP ',
    'summary': 'Modulo de Tipo de cambio del día - Perú',
    'description': '''  ''',
    'website': 'hhttp://www.sofiaerp.com/facturacion-electronica',
    'depends': ['base','account'],
    "data": [
        'views/res_currency_view.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_company_views.xml',
            ], 
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'sequence': 1,
    'support': 'modulos@sofiaerp',
}
