# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'EDI for Peru extends',
    'icon': '/l10n_pe/static/description/icon.png',
    'version': '0.1',
    'summary': 'Electronic Invoicing for Peru (OSE method) and UBL 2.1',
    'category': 'Accounting/Localizations/EDI',
    'author': 'Vauxoo',
    'license': 'OEEL-1',
'description': """
EDI Peru Localization extends
    """,
    'depends': [
        'l10n_pe_edi',
    ],
    "data": [
        'views/retencion.xml',
        #'data/retencion.xml',         
    ],
    'installable': True,
}
