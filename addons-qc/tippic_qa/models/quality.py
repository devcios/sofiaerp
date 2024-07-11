# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, exceptions, _

_logger = logging.getLogger(__name__)

class QualityTest(models.Model):
    _name = 'tippic_qa.quality_test'
    _description = 'Esta es la Prueba que se va a ejecutar en base al punto de control que se va a usar'

    quality_measure = fields.Many2one('quality.measure', string='Measure', index=True, ondelete='cascade',
                                      track_visibility='onchange')
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done'), ('cancel', 'Cancel')],
                default='draft',
                tracking=True,
                string='Estado')
    quality_point = fields.Many2one('tippic_qa.control_point', string='Punto de Control', ondelete='cascade')
    date = fields.Datetime(default=lambda self: fields.Datetime.now(), string='Fecha')
    tag_ids = fields.Many2many('tippic_qa.tags', string='Tags', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    nonconformity = fields.Float(string='Disconformidad', track_visibility='onchange', default=0)
    fulfillment = fields.Selection(
        selection=[('satisfied', 'Satisfecho'), ('unsatisfied', 'Insatisfecho')],
        store=True,
        string='Cumplimiento', track_visibility='onchange')
    quality_control_id = fields.Many2one('tippic_qa.quality_control', string='Control de calidad')

    def unlink(self):
        pass


    def mark_fail(self):
        """
        - Vamos a asumir que todos los lotes van a estar siempre en un inicio en la ubicación de cuarentena
        - cuando se genera un movimiento se cambia la cantidad de producto desechado en la orden de producción
        :return:
        """
        for record in self:
            if record.nonconformity > 0:

                config_obj = self.env['res.config.settings'].create({})

                if not config_obj.operation_scrap.default_location_src_id.id:
                    raise exceptions.UserError(_('Tienes que configurar la operación de Scrap en Settings.'))

                scrap_class = self.env['stock.scrap']

                new_scrap_obj = scrap_class.create({
                    'product_id': record.product_id.id,
                    'product_uom_id': record.product_id.uom_id.id,
                    'production_id': record.quality_control_id.production_id.id,
                    'location_id': config_obj.operation_scrap.default_location_src_id.id,
                    'lot_id': record.quality_control_id.lot_id.id,
                    'scrap_qty': record.nonconformity
                })
                new_scrap_obj.do_scrap()

                if new_scrap_obj.move_id:
                    for line in new_scrap_obj.move_id.move_line_ids:
                        record.quality_control_id.add_move_line_to_move_line_dest_ids(line)

                order = self.env['mrp.production'].search([('id', '=', record.quality_control_id.production_id.id)],
                                                          limit=1)

                order.modify_nonconformity(amount=record.nonconformity)  # Modificamos la cantidad de no conformes

                record.write({'fulfillment': 'unsatisfied', 'state': 'done'})

            else:
                raise exceptions.UserError(_('La cantidad no conforme debe ser mayor a 0.'))

    def mark_pass(self):
        for record in self:
            record.write({'fulfillment': 'satisfied', 'state': 'done'})


class QualityControl(models.Model):
    _name = 'tippic_qa.quality_control'
    _description = 'Control de calidad'
    _inherit = 'mail.thread'
    _order = 'id desc'

    name = fields.Char('Name', required=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('tippic_qa.quality_control'))
    
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmado'), ('done', 'Terminado'), ('cancel', 'Cancelar')],
                             default='draft', tracking=True, string='Estado')
    
    product_id = fields.Many2one('product.product', string='Product', index=True, ondelete='cascade',
                                 track_visibility='onchange')
    product_template_id = fields.Many2one('product.template', string='Product Template',
                                          related='product_id.product_tmpl_id')
    type = fields.Many2one('tippic_qa.control_type', string='Tipo', index=True, ondelete='cascade')
    origin = fields.Char(string='Documento de origen')
    move_id = fields.Many2one('stock.move', string='Movimiento origen', index=True)
    date = fields.Datetime(default=lambda self: fields.Datetime.now(), string='Fecha')
    quantity_min = fields.Float('Min-Value', track_visibility='onchange')
    quantity_max = fields.Float('Max-Value', track_visibility='onchange')
    tests = fields.One2many('tippic_qa.quality_test', 'quality_control_id', string='Pruebas', ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Responsables')
    company_id = fields.Many2one('res.company', string='Compañia')
    production_id = fields.Many2one('mrp.production', string='Orden de Producción')
    move_line_dest_ids = fields.Many2many('stock.move.line', string='Lineas de Destino')
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company.id)
    date_stop = fields.Datetime(string='Fecha de inicio')
    date_delay = fields.Datetime(string='Fecha de finalización')
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True,
        states={'done': [('readonly', True)]}, help="Lot/Serial of Production.")
  
    @api.model
    def create(self, vals):
        user_id = self.env.user.id
        company_id = self.env.user.company_id.id
        vals['user_id'] = user_id
        vals['company_id'] = company_id

        # Crea el registro con los valores actualizados
        return super(QualityControl, self).create(vals)

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def action_confirm(self):
        for record in self:
            record.write({'state': 'confirm'})

    def action_terminar(self):
        for record in self:
            """
            - Creamos el movimiento para hacer el cambio de ubicación
            - Vamos a validar si es que type no esta vació para forzar que tenga un tipo seleccionado
            """
            if record.type:

                counter = 0

                for check in record.tests: # Con esto vamos a validar que los estados estén en realizado
                    if check.state == 'draft':
                        counter += 1

                config_obj = self.env['res.config.settings'].create({})

                # Esto lo podemos poner en una función para verificar las configuraciones
                if not config_obj.operation_quarantine.default_location_src_id.id:
                    raise exceptions.UserError(_('Tienes que configurar la operación de Cuarentena en Settings.'))

                if counter > 0:
                    raise exceptions.UserError(_('Todas las pruebas tienen que ser realizadas.'))

                sequence = self.env['ir.sequence'].next_by_code('stock.move')

                stock_move = self.env['stock.move'].create({
                    'name': f'QC/{sequence}',
                    'product_id': record.product_id.id,
                    'product_uom_qty': record.lot_id.product_qty,
                    'product_uom': record.product_id.uom_id.id,
                    'location_id': config_obj.operation_quarantine.default_location_src_id.id,  # Ubicación de origen
                    'location_dest_id': config_obj.operation_quarantine.default_location_dest_id.id,  # Ubicación de destino
                    'move_line_ids': [(0, 0, {
                        'product_id': record.product_id.id,
                        'product_uom_id': record.product_id.uom_id.id,
                        'location_id': config_obj.operation_quarantine.default_location_src_id.id,
                        'location_dest_id': config_obj.operation_quarantine.default_location_dest_id.id,
                        'qty_done': record.lot_id.product_qty,
                        'lot_id': record.lot_id.id,  # Especifica el ID del lote aquí
                    })],
                    # Otros campos relacionados con el movimiento de stock, si es necesario
                })

                stock_move._action_confirm()  # Aquí confirmamos el movimiento
                stock_move._action_done()  # Aquí confirmamos el movimiento

                for line in stock_move.move_line_ids:
                    record.add_move_line_to_move_line_dest_ids(line)

                record.write({'state': 'done'})
            else:
                raise exceptions.UserError(_('Tienes que seleccionar un tipo de control de calidad.'))


    def add_move_line_to_move_line_dest_ids(self, obj):
        for record in self:
            record.write({'move_line_dest_ids': [(4, obj.id)]})


