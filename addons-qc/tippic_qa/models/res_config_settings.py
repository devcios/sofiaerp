# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class TippicQaResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Configuración del Modulo'

    operation_quarantine = fields.Many2one('stock.picking.type', string='Operación de cuarentena', config_parameter='tippic_qa.operation_quarantine')
    operation_scrap = fields.Many2one('stock.picking.type', string='Operación de descarte', config_parameter='tippic_qa.operation_scrap')