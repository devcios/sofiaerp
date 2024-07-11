# -*- coding: utf-8 -*-

from odoo import models, fields, api


class sit_tracking_production_produced(models.Model):
    _name = 'sit_tracking_production_produced'
#     _description = 'sit_tracking_production.sit_tracking_production'
    sit_mrp_workorder = fields.Many2one('mrp.workorder', string='Production ID', readonly=False)

    date = fields.Datetime(string='Fecha')
    product_id = fields.Many2one(string="Producto", comodel_name='product.product')
    # lot_id = fields.Many2one(string="Lote", comodel_name='stock.production.lot')
    qty_done = fields.Float(string="Cant Hecha")
    product_uom_id = fields.Many2one(string="Unidad de medida", comodel_name='product.uom')
    state =  fields.Selection([
        ('draft', "Nuevo"), 
        ('cancel', "Cancelado"),
        ('waiting', "Esperando otro movimiento"), 
        ('confirmed', "Esperando disponibilidad"),
        ('partially_available', "Parcialmente disponible"), 
        ('assigned', "Disponible"), 
        ('done', "Realizado")], 
        )
    blocktime_duration_inicial = fields.Float(string="Duración_inicial(min)")
    blocktime_duration = fields.Float(string="Duración(min)")
    qty_unitario = fields.Float(string="Qty Unitaria")
