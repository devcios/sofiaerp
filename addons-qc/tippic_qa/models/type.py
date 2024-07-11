# -*- coding: utf-8 -*-
from odoo import api, fields, models


class QualityControlType(models.Model):
    _name = 'tippic_qa.control_type'
    _description = 'Tipos de Control de Calidad'

    name = fields.Char(string='Nombre')
    active = fields.Boolean(string='Activo', default=True)
    internal_type = fields.Selection([
        ('picking', 'Guía de Remision'),
        ('other', 'Otro'),
        ('mrp', 'Producción')
    ], default='picking', string='Tipo interno')
    default_generate = fields.Selection([
        ('scrap', 'Scrap'),
        ('return', 'Return Goods'),
        ('refound', 'To refound')
    ], default='scrap', string='Default Generate')
    process_move_dest = fields.Boolean(default=False, string='Proces move dest')
    sequence = fields.Integer(string='Secuencia')