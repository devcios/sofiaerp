# -*- coding: utf-8 -*-
from odoo import fields, models, api


class TemperatureLine(models.Model):

    _name = "car.temperature"

    name = fields.Char(string="Nombre")
    date_actual = fields.Datetime(string="Fecha y Hora", default=fields.Datetime.now)
    t_visor = fields.Float(string="T° Visor")
    t_system = fields.Float(string="T° Sistema")
    temperature_id = fields.Many2one('car.rental.contract', string="Temperaturas", on_delete='set null', store=True, copy=True)