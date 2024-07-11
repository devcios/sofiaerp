from odoo import fields, models

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    scrap_comment = fields.Char(string='Motivo de desecho')