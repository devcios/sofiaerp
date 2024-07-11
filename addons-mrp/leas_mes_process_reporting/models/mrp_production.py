# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import datetime
import math
import re

from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
from odoo.tools.misc import OrderedSet, format_date, groupby as tools_groupby

from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES

from odoo.http import request
import logging
_logger = logging.getLogger(__name__)


SIZE_BACK_ORDER_NUMERING = 3


class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _inherit = 'mrp.production'
    
    sit_hay_orden_de_trabajo = fields.Boolean("Hay orden de trabajo ?", compute='_onchange_workorder_idss')


    @api.onchange('workorder_ids')
    def _onchange_workorder_idss(self):
        for line in self:
            if line.workorder_ids:
                line.sit_hay_orden_de_trabajo = True
            else:
                line.sit_hay_orden_de_trabajo = False


    def action_confirm(self):
        self._check_company()
        for production in self:
            if production.bom_id:
                production.consumption = production.bom_id.consumption
            # In case of Serial number tracking, force the UoM to the UoM of product
            if production.product_tracking == 'serial' and production.product_uom_id != production.product_id.uom_id:
                production.write({
                    'product_qty': production.product_uom_id._compute_quantity(production.product_qty, production.product_id.uom_id),
                    'product_uom_id': production.product_id.uom_id
                })
                for move_finish in production.move_finished_ids.filtered(lambda m: m.product_id == production.product_id):
                    move_finish.write({
                        'product_uom_qty': move_finish.product_uom._compute_quantity(move_finish.product_uom_qty, move_finish.product_id.uom_id),
                        'product_uom': move_finish.product_id.uom_id
                    })
            production.move_raw_ids._adjust_procure_method()
            (production.move_raw_ids | production.move_finished_ids)._action_confirm(merge=False)
            production.workorder_ids._action_confirm()
        # run scheduler for moves forecasted to not have enough in stock
        _logger.info("SIT self.move_raw_ids[0] =%s",self.move_raw_ids)
        if self.move_raw_ids:
            self.move_raw_ids[0]._trigger_scheduler()
        self.picking_ids.filtered(
            lambda p: p.state not in ['cancel', 'done']).action_confirm()
        self.filtered(lambda mo: mo.state == 'draft').state = 'confirmed'
        return True




    def completar_lote_subproductos(self):
        _logger.info("SIT self.move_byproduct_ids=%s", self.move_byproduct_ids)
        stock_lot = self.env['stock.production.lot']
        lote = self.lot_producing_id.name
        company_id = self.company_id
        for sub_product in self.move_byproduct_ids:
            if not sub_product.lot_ids:

                lot_vals = {
                    'name': lote,                # Nombre del lote
                    'product_id': sub_product.product_id.id,
                    'product_uom_id': sub_product.product_id.uom_id.id,
                    'company_id': company_id.id,
                    'product_qty': sub_product.product_uom_qty,
                }
                move = stock_lot.sudo().create(lot_vals)
                move_line_ids = self.env['stock.move.line'].search([('id','=', move.id)])
                _logger.info("SIT move_line_ids =%s", sub_product.move_line_ids) 
                _logger.info("SIT move_line_ids =%s", sub_product.move_line_ids) 
                MENSAJE = "SIT completar_lote_subproductos move =" + str(move)

                # raise UserError(_(MENSAJE))
                move_vals = {
                    'move_id': sub_product.id,
                    'company_id': company_id.id,
                    'product_id': sub_product.product_id.id,
                    'product_uom_id': sub_product.product_id.uom_id.id,
                    'qty_done': sub_product.product_uom_qty,
                    'lot_id': move.id,
                    'location_id': sub_product.location_id.id,
                    'location_dest_id': sub_product.location_dest_id.id,
                    'state': 'done',                         #done
                    'reference': self.name,                #WH/MO/00101 
                }
                MOVE_LINE = move_line_ids.create(move_vals)
                MENSAJE = "SIT MOVE_LINE = " + str(MOVE_LINE)
                # sub_product.lot_ids = move
                # raise UserError(_(MENSAJE))
        return


    def completar_lote_consumible(self):
        _logger.info("SIT self.move_raw_ids[0]=%s", self.move_raw_ids[0])
        MENSAJE = "SIT completar_lote_consumible self.move_raw_ids[0] =" + str(self.move_raw_ids[0].allowed_operation_ids) + "-" + str(self.move_raw_ids[0])

        # raise UserError(_(MENSAJE))
        stock_lot = self.env['stock.production.lot']
        lote = self.lot_producing_id.name
        company_id = self.company_id
        for sub_product in self.move_raw_ids:
            # if not sub_product.lot_ids:
            
                # move_line_ids = self.env['stock.move.line'].search([('move_id','=', self.move_raw_ids[0].id)])
                move_line_ids = self.env['stock.move.line'].search([('move_id','=', sub_product.id)])
                _logger.info("SIT completar_lote_consumible self.move_raw_ids[0] =%s", sub_product) 
                _logger.info("SIT completar_lote_consumible move_line_ids =%s", move_line_ids) 
                _logger.info("SIT completar_lote_consumible should_consume_qty =%s", sub_product.should_consume_qty) 

                
                MENSAJE = "SIT completar_lote_consumible move_line_ids =" + str(sub_product.should_consume_qty)
                # raise UserError(_(MENSAJE))

                move_line_ids.qty_done = sub_product.product_qty
                # move_line_ids.qty_done = sub_product.should_consume_qty


                
        return
    

    #VISTA form
    def sit_view_work_order(self):
        MENSAJE = "Orden de trabajo"
    
        ordenes_trabajo = self.workorder_ids
        _logger.info("SIT ordenes_trabajo=%s , len(ordenes_trabajo)= %s", ordenes_trabajo, len(ordenes_trabajo))
        
        if ordenes_trabajo:
            if len(ordenes_trabajo) == 1:    
                return {
                    'name': 'Orden de Trabajo',
                    'type': 'ir.actions.act_window',
                    'res_model': 'mrp.workorder',
                    'view_mode': 'form',
                    'res_id': ordenes_trabajo.id,
                    'view_id': False,
                }
            else:
                MENSAJE = "Se requiere 1 orden de trabajo para poder ver detalle."
                raise UserError(_(MENSAJE))

        else:
            return "No se encontraron tipos de picking."
    #Vsta tablet
    def action_mrp_workorder_view_form_tablet(self):
        MENSAJE = "Orden de trabajo (T)"
        ordenes_trabajo = self.workorder_ids
        view_id = self.env.ref('leas_mes_process_reporting.mrp_workorder_view_form_tablet').id
    
        _logger.info("SIT ordenes_trabajo=%s , len(ordenes_trabajo)= %s", ordenes_trabajo, len(ordenes_trabajo))

       
        if ordenes_trabajo:
            if len(ordenes_trabajo) == 1:    
                return {
                    'name': 'Orden de Trabajo',
                    'type': 'ir.actions.act_window',
                    'res_model': 'mrp.workorder',
                    'target': 'fullscreen',
                    'view_mode': 'form',
                    'res_id': ordenes_trabajo.id,
                    'view_id': view_id,
                    'flags': {
                        'withControlPanel': False,
                        'form_view_initial_mode': 'edit',
                    },                    
                }
            else:
                MENSAJE = "Se requiere 1 orden de trabajo para poder ver detalle."
                raise UserError(_(MENSAJE))

        else:
            return "No se encontraron tipos de picking."
                
    def button_mark_donee(self):
        # self.completar_lote_consumible()
        for componente in self.move_raw_ids:
            _logger.info("SIT -------------------------------------- componente=%s", componente)
            if not componente.lot_ids:
                MENSAJE = "Componente " + componente.product_id.name + " no tienen número de lote, registrar lote de componente"
                raise UserError(_(MENSAJE))
        if self.move_byproduct_ids:
            if self.move_byproduct_ids:
                self.completar_lote_subproductos()
                for subprod in self.move_byproduct_ids:
                    _logger.info("SIT -------------------------------------- subproduct=%s", subprod)
                    if not subprod.lot_ids:
                        MENSAJE = "Componente: " + subprod.product_id.name + " no tienen número de lote, registrar lote de subproductos"
                        raise UserError(_(MENSAJE))
                _logger.info("SIT self.move_raw_ids[0]=%s", self.move_raw_ids[0])


        # A mano, especificar lote de producto terminado
        # A mano, especificar lote de consumibles
        # _logger.info("SIT action_mrp_workorder_view_form_tablet = %s", self)
        # #Obtiene el nombre del lote.
        # _logger.info("SIT action_mrp_workorder_view_form_tablet lot_producing_id = %s(%s)", self.lot_producing_id, self.lot_producing_id.name)
        # _logger.info("SIT ---------------=========-----======-----------=-======-----=========---------" )

        # # CONSUMIDOS
        # # _logger.info("SIT action_mrp_workorder move_raw_ids = %s", self.move_raw_ids[0])
        # _logger.info("SIT action_mrp_workorder product_qty = %s", self.move_raw_ids[0].product_qty)
        # _logger.info("SIT action_mrp_workorder quantity_done = %s", self.move_raw_ids[0].quantity_done)
        # _logger.info("SIT action_mrp_workorder move_raw_ids = %s", self.move_raw_ids[0].search_read([('id','=', self.move_raw_ids[0].id)]))
        # _logger.info("SIT ---------------===============================----------------------------" )
        
        # for subproduct in self.move_byproduct_ids:
        
        #     # _logger.info("SIT action_mrp_workorder move_byproduct_ids = %s", subproduct.search_read([('id','=', subproduct.id)]))
        #     _logger.info("SIT action_mrp_workorder product_uom_qty = %s", subproduct.product_uom_qty)
        #     _logger.info("SIT action_mrp_workorder quantity_done = %s", subproduct.quantity_done)
        #     _logger.info("SIT action_mrp_workorder lot_ids = %s", subproduct.lot_ids)
        # _logger.info("SIT -------------------------------------------" )
        # _logger.info("SIT action_mrp_workorder work_order_ids = %s", self.workorder_ids)
        # _logger.info("SIT action_mrp_workorder qty_operation_avail = %s", self.workorder_ids.qty_operation_avail)
        # _logger.info("SIT action_mrp_workorder qty_operation_wip = %s", self.workorder_ids.qty_operation_wip)
        # _logger.info("SIT action_mrp_workorder qty_operation_comp = %s", self.workorder_ids.qty_operation_comp)
        # _logger.info("SIT -----------------///1111111111111111////--------------------------" )
        # #Busca el lote para el consumible   lot_ids
        # _logger.info("SIT action_mrp_workorder lot_ids = %s", self.move_raw_ids[0].lot_ids)
        # #Busca el qty a realizar  para el consumible
        # _logger.info("SIT action_mrp_workorder product_qty = %s", self.move_raw_ids[0].product_qty)
        # #Ubicación en almacen   location_id  -->   location_dest_id
        # _logger.info("SIT action_mrp_workorder location_id = %s", self.move_raw_ids[0].location_id)
        # _logger.info("SIT action_mrp_workorder location_dest_id = %s", self.move_raw_ids[0].location_dest_id)
        # # producción de origen  nombre=origin
        # _logger.info("SIT action_mrp_workorder origin = %s", self.move_raw_ids[0].origin)
        # # linea_ids:   move_line_ids
        # _logger.info("SIT action_mrp_workorder move_line_ids = %s", self.move_raw_ids[0].move_line_ids)
        # _logger.info("SIT action_mrp_workorder move_line_ids = %s", self.move_raw_ids[0].move_line_ids.search_read([('id','=', self.move_raw_ids[0].id)]))

        # Busca todos los consumibles que tengan        
        # _logger.info("SIT action_mrp_workorder workorder_ids = %s", self.workorder_ids.search_read([('id','=', self.workorder_ids.id)]))
        _logger.info("SIT __________________________________ super button_mark_done")
        super(MrpProduction, self).button_mark_done()





    def button_mark_done(self):
        for componente in self.move_raw_ids:
            _logger.info("SIT -------------------------------------- componente=%s", componente)
            if not componente.lot_ids:
                MENSAJE = "Componente " + componente.product_id.name + " no tienen número de lote, registrar lote de componente"
                raise UserError(_(MENSAJE))
        if self.move_byproduct_ids:
            if self.move_byproduct_ids:
                self.completar_lote_subproductos()
                for subprod in self.move_byproduct_ids:
                    _logger.info("SIT -------------------------------------- subproduct=%s", subprod)
                    if not subprod.lot_ids:
                        MENSAJE = "Componente: " + subprod.product_id.name + " no tienen número de lote, registrar lote de subproductos"
                        raise UserError(_(MENSAJE))
                _logger.info("SIT self.move_raw_ids[0]=%s", self.move_raw_ids[0])






        self._button_mark_done_sanity_checks()
        _logger.info("SITSIT self =%s", self)
        if not self.env.context.get('button_mark_done_production_ids'):
            self = self.with_context(button_mark_done_production_ids=self.ids)
        res = self._pre_button_mark_done()
        _logger.info("SITSIT res =%s", res)
        _logger.info("SITSIT res =%s", type(res))

        if res is not True:
            return res
        _logger.info("SITSIT res =%s", type(res))
        
        _logger.info("SITSIT self.env.context.get('mo_ids_to_backorder' =%s", self.env.context.get('mo_ids_to_backorder') )

        if self.env.context.get('mo_ids_to_backorder'):
            productions_to_backorder = self.browse(self.env.context['mo_ids_to_backorder'])
            productions_not_to_backorder = self - productions_to_backorder
            close_mo = False
        else:
            productions_not_to_backorder = self
            productions_to_backorder = self.env['mrp.production']
            close_mo = True
        _logger.info("SITSIT productions_to_backorder =%s", productions_to_backorder)
        _logger.info("SITSIT productions_not_to_backorder =%s", productions_not_to_backorder)

        self.workorder_ids.button_finish()

        backorders = productions_to_backorder._generate_backorder_productions(close_mo=close_mo)
        productions_not_to_backorder._post_inventory(cancel_backorder=True)
        productions_to_backorder._post_inventory(cancel_backorder=True)

        # if completed products make other confirmed/partially_available moves available, assign them
        done_move_finished_ids = (productions_to_backorder.move_finished_ids | productions_not_to_backorder.move_finished_ids).filtered(lambda m: m.state == 'done')
        done_move_finished_ids._trigger_assign()

        # Moves without quantity done are not posted => set them as done instead of canceling. In
        # case the user edits the MO later on and sets some consumed quantity on those, we do not
        # want the move lines to be canceled.
        (productions_not_to_backorder.move_raw_ids | productions_not_to_backorder.move_finished_ids).filtered(lambda x: x.state not in ('done', 'cancel')).write({
            'state': 'done',
            'product_uom_qty': 0.0,
        })

        for production in self:
            production.write({
                'date_finished': fields.Datetime.now(),
                'product_qty': production.qty_produced,
                'priority': '0',
                'is_locked': True,
                'state': 'done',
            })

        for workorder in self.workorder_ids.filtered(lambda w: w.state not in ('done', 'cancel')):
            workorder.duration_expected = workorder._get_duration_expected()

        if not backorders:
            if self.env.context.get('from_workorder'):
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'mrp.production',
                    'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                    'res_id': self.id,
                    'target': 'main',
                }
            return True
        context = self.env.context.copy()
        context = {k: v for k, v in context.items() if not k.startswith('default_')}
        for k, v in context.items():
            if k.startswith('skip_'):
                context[k] = False
        action = {
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'context': dict(context, mo_ids_to_backorder=None, button_mark_done_production_ids=None)
        }
        if len(backorders) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': backorders[0].id,
            })
        else:
            action.update({
                'name': _("Backorder MO"),
                'domain': [('id', 'in', backorders.ids)],
                'view_mode': 'tree,form',
            })
        return action
