# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    point_of_controls_id = fields.Many2many(
        comodel_name='tippic_qa.control_point',
        relation='tippic_qa_control_point_producto_tmplt',
        column1='producto_template_id',
        column2='control_point_id',
        string='Puntos de Control'
    )