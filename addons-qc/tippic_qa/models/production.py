 # -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, exceptions, _

_logger = logging.getLogger(__name__)


class ProductionMRP(models.Model):
    _description = 'Herencia de la clase MRP'
    _inherit = 'mrp.production'

    quantity_waste = fields.Float(default=0)
    reprocess = fields.Float(default=0)
    nonconformity = fields.Float(default=0)
    qa_order_id = fields.Many2one('tippic_qa.quality_control', string='Orden para Pruebas', index=True)
    test_count = fields.Float(compute='_test_counter', store=True)
    test_count_not_done = fields.Float(default=0)

    @api.onchange('qty_producing', 'lot_producing_id')
    def _onchange_lot_producing_id(self):
        if len(self.move_byproduct_ids) > 0:
            for move_byproduct in self.move_byproduct_ids:
                if not move_byproduct.move_line_ids:
                    new_name = self.env['ir.sequence'].next_by_code('stock.production.lot')

                    lot_values = {
                        'name': new_name,  # Reemplaza 'Número_de_lote' con el nombre de tu lote
                        'product_id': move_byproduct.product_id.id,  # Reemplaza 'producto_id' con el ID del producto asociado al lote
                        'company_id': move_byproduct.company_id.id,  # Reemplaza 'company_id' con el ID de la compañía si es relevante
                    }

                    new_lot = self.env['stock.production.lot'].create(lot_values)

                    move_line_values = {
                        'product_id': move_byproduct.product_id.id,
                        'lot_id': new_lot.id,
                        'location_id': move_byproduct.location_id.id,
                        'location_dest_id': move_byproduct.location_dest_id.id,
                        'move_id': move_byproduct.id,
                        'product_uom_id': move_byproduct.product_uom.id,
                        'qty_done': move_byproduct.product_qty,
                    }
                    new_move_line = self.env['stock.move.line'].create(move_line_values)
                else:
                    _logger.info('===============================No hay linea================================')
        else:
            _logger.info('===============================No hay ByProducts================================')

    def action_go_to_qa_test_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Control de Calidad',
            'res_model': 'tippic_qa.quality_control',
            'view_mode': 'form',
            'res_id': self.qa_order_id.id,
            'target': 'current'
        }

    def add_qa_order_to_mrp_id(self, obj):
        self.ensure_one()
        self.write({'qa_order_id': obj.id})

    @api.depends('qa_order_id')
    def _test_counter(self):
        for record in self:
            if record.qa_order_id:
                record.test_count = len(record.qa_order_id)  # Contar la cantidad de controles de calidad
            else:
                record.test_count = 0


    def modify_nonconformity(self, amount):
        self.ensure_one()  # Asegura que solo estamos tratando con un único registro
        new_nonconformity = self.nonconformity + amount
        self.write({'nonconformity': new_nonconformity})

    def _get_product_id(self):
        return self.product_id.id

    def _get_product_template_id(self):
        return self.product_id.product_tmpl_id.id

    def button_mark_done(self):
        """
        Cuando se ejecuta la acción de confirmación se crea la orden de la prueba y el detalle de las pruebas que se van a necesitar
        """
        res = super(ProductionMRP, self).button_mark_done()

        product_template_id = self._get_product_template_id()
        product_id = self._get_product_id()

        if self.product_tmpl_id.tracking != 'lot':
            raise exceptions.UserError(_('El producto no esta configurado para usar lotes.'))
        
        list_of_moves_line = []
        for move in self.move_finished_ids:
            if move.product_id == self.product_id:
                for line in move.move_line_ids:
                    list_of_moves_line.append(line)

        if not list_of_moves_line:
            _logger.warning('No se encontraron líneas de movimiento para el producto %s. Se eliminará la orden de control de calidad si no tiene líneas de movimiento procesadas.', product_id)
            if self.qa_order_id and not self.qa_order_id.move_line_dest_ids.filtered(lambda line: line.state == 'done'):
                self.qa_order_id.unlink()  # Eliminar la orden de control de calidad si no tiene líneas de movimiento procesadas
            return res

        order_model = self.env['tippic_qa.quality_control'] #  Con esto obtenemos la clase para crear una orden de testing

        order_data = {
            'state': 'draft',
            'product_id': self.product_id.id,
            'origin': self.name,
            'product_template_id': self.product_tmpl_id.id,
            'production_id': self.id,
            'lot_id': self.lot_producing_id.id
        }

        new_order_obj = order_model.create(order_data)  # Crear la orden de prueba

        product_template = self.env['product.template'].browse(product_template_id)
        related_objects = product_template.point_of_controls_id

        test_data_list = []
        list_of_moves_line = []

        for test in related_objects:
            test_data = {
                'quality_point': test.id,
                'product_id': product_id,
                'quality_control_id': new_order_obj.id
            }
            test_data_list.append(test_data)

        if test_data_list:
            new_order_obj.write({
                'tests': [(0, 0, test_data) for test_data in test_data_list]
            })
        else:
            raise exceptions.UserError(_('Verifica que el producto tenga pruebas asignadas.'))

        self.add_qa_order_to_mrp_id(obj=new_order_obj) # Con esto agregamos la orden de pruebas a la orden de producción

        # Con esto vamos a agregar los movimientos a la orden de pruebas
        # if self.move_finished_ids:
        #    for move in self.move_finished_ids:
        #        for line in move.move_line_ids:
        #            list_of_moves_line.append(line)

        if self.move_finished_ids:
            for move in self.move_finished_ids:
                if move.product_id == self.product_id:  # Verifica si es el producto principal
                    for line in move.move_line_ids:
                        list_of_moves_line.append(line)

        if list_of_moves_line:
            new_order_obj.write({'move_line_dest_ids': [(4, move.id) for move in list_of_moves_line ]})
            _logger.info('Se agregaron las lineas de forma correcta.')

        _logger.info('La función action_confirm se ejecutó correctamente y creo la orden de Control de calidad %s',
                     new_order_obj.name)

        if self.move_byproduct_ids:  # Con esto creamos la orden para los subproductos =/ esto tiene que ser optimizado
            for item in self.move_byproduct_ids:

                item._action_confirm()
                item._action_done()

                list_of_moves_byproducts_line = []

                order_sub_model = self.env['tippic_qa.quality_control']

                product_sub_template = self.env['product.template'].browse(item.product_tmpl_id.id)

                for line in item.move_line_ids:
                    list_of_moves_byproducts_line.append(line)

                point_of_control_sub = product_sub_template.point_of_controls_id  # Lista de pruebas

                if point_of_control_sub: # Con esto validamos si el producto tiene pruebas asignadas

                    order_sub_data = {
                        'state': 'draft',
                        'product_id': item.product_id.id,
                        'origin': product_sub_template.name,
                        'product_template_id': product_sub_template.id,
                        'production_id': self.id
                    }

                    new_order_sub = order_sub_model.create(order_sub_data)

                    _logger.info('Se va a crear una orden de prueba para el movimiento es %s',
                                 new_order_sub.name)

                    for test_sub in point_of_control_sub: # Con esto creamos las pruebas de los subproductos

                        t = self.env['tippic_qa.quality_test']

                        test_sub_data = {
                            'quality_point': test_sub.id,
                            'product_id': item.product_id.id,
                            'quality_control_id': new_order_sub.id
                        }

                        obj = t.create(test_sub_data)

                        _logger.info('Se agrego la siguiente prueba %s',
                                     obj.id)

                        new_order_sub.write({'tests': [(4, obj.id)]})


                    if list_of_moves_byproducts_line:  # Con esto agregamos la línea a la lista de movimientos
                        new_order_sub.write(
                            {
                                'move_line_dest_ids': [(4, move.id) for move in list_of_moves_byproducts_line],
                            }
                        )

                        for line in list_of_moves_byproducts_line:
                            new_order_sub.write(
                                {
                                    'lot_id': line.lot_id.id,
                                    'origin': line.reference,
                                    'move_id': line.move_id.id
                                }
                            )
                else:
                    raise exceptions.UserError(_('El producto %s no tiene pruebas asignadas.', item.product_tmpl_id.id))

        return res