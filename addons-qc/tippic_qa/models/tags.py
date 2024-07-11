# -*- coding: utf-8 -*-
from odoo import api, fields, models


class QualityTags(models.Model):
    _name = 'tippic_qa.tags'
    _description = 'Etiquetas de Calidad'

    name = fields.Char(string='Nombre')