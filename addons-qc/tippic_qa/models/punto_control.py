# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PuntoControl(models.Model):
    _name = 'tippic_qa.control_point'
    _description = 'Lista de Puntos de Control'

    name = fields.Char(string='Punto de Control')
    active = fields.Boolean(string='Activo', default=True)
    product_ids = fields.Many2many(
        comodel_name='product.template',
        relation='tippic_qa_control_point_product_template_rel',
        string='Productos',
        ondelete='restrict')
    sequence = fields.Integer(string='Secuencia')
    delay = fields.Float(string='Retraso (hr)')
    type = fields.Selection([
        ('quality', 'Cualitativo'),
        ('quantity', 'Cuantitativo')
    ], default='cualitativo', tracking=True, string='Tipo de Prueba')
    quantity_min = fields.Float('Valor Minimo', track_visibility='onchange')
    quantity_max = fields.Float('Valor Maximo', track_visibility='onchange')
    nonconformity_type = fields.Selection([
        ('reprocess', 'Reprocesar'),
        ('nonconformity', 'No Conformidad')
    ], default='reprocess', tracking=True, string='Tipo de Control')
    trigger_time = fields.Many2many(
        comodel_name='stock.picking.type',
        string='Disparador encendido',
        ondelete='restrict'
    )
    test_id = fields.Many2one('tippic_qa.quality_test', string='Test')
    taxes_id = fields.Many2many(
        comodel_name='account.tax',
        relation='tippic_qa_control_point_account_tax_rel',
        column1='control_point_id',
        column2='tax_id',
        string='Impuestos'
    ) #  Me da miedo sacar

    def _add_test_to_product(self, product):
        product_template = self.env['product.template'].search([('id', '=', product.id)], limit=1)

        if product_template:
            if not self in product_template.point_of_controls_id:
                product_template.write({'point_of_controls_id': [(4, self.id)]})

    def write(self, vals):
        res = super(PuntoControl, self).write(vals)

        if 'product_ids' in vals:
            for product in self.product_ids:
                self._add_test_to_product(product)

        return res

