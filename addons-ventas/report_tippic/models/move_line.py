from typing import Any

from odoo import fields, models, api
from datetime import datetime


class LineReport(models.Model):
    _inherit = "account.invoice.report"

    default_code = fields.Char(related="product_id.default_code", String='Codigo')
    name_product = fields.Char(related="product_id.name", String='Articulo')
    name_currency = fields.Char(related="move_id.currency_id.name", String='Moneda')
    rate_change_match = fields.Float(string="Cambio", compute='_compute_rate_ids_match', digits=(16, 3))
    unit_product = fields.Char(related="product_id.unit_product", String='Unidad de Negocio')
    line_product = fields.Char(related="product_id.line_product", String='Linea')
    price_unit = fields.Float(string="PU", compute='_compute_price_unit')
    price_total = fields.Float(string="Subtotal", compute='_compute_price_subtotal')

    @api.depends('move_id.currency_id.rate_ids', 'invoice_date')
    def _compute_rate_ids_match(self):
        for report in self:
            matching_change = 0.0
            for rate in report.move_id.currency_id.rate_ids:
                if rate.name == report.invoice_date:
                    matching_change = rate.rate_pe
                    break
            report.rate_change_match = matching_change

    @api.depends('move_id')
    def _compute_price_unit(self):
        for rec in self:
            move_lines = self.env['account.move.line'].search([
                ('move_id', '=', rec.move_id.id),
                ('product_id', '=', rec.product_id.id)
            ])
            if move_lines:
                rec.price_unit = move_lines[0].price_unit
            else:
                rec.price_unit = 0.0
				
    @api.depends('move_id')
    def _compute_price_subtotal(self):
        for rec in self:
            move_lines = self.env['account.move.line'].search([
                ('move_id', '=', rec.move_id.id),
                ('product_id', '=', rec.product_id.id)
            ])
            if move_lines:
                rec.price_total = move_lines[0].price_subtotal
            else:
                rec.price_total = 0.0