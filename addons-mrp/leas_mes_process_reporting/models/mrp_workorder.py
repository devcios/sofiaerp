# -*- coding: utf-8 -*-
import ast

from odoo import models, fields, _, api
import json
import os
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools import float_round
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    # Used to create input fields in the interface to facilitate user input of information.

    code = fields.Char('Code', readonly=True)
    reporting_point = fields.Boolean(related='operation_id.reporting_point', default=True, store=True)
    qty_operation_wip = fields.Float('Cant. En-Proceso')
    qty_operation_comp = fields.Float('Cant. Completada')
    qty_operation_avail = fields.Float('Cant. Disponible', compute='_compute_qty_operation_avail')
    wo_Proc_chart_data = fields.Char('Proceso de Orden de Trabajo', compute='_compute_Proc_chart_data')
    mo_Proc_chart_data = fields.Char('Proceso de Producción', compute='_compute_Proc_chart_data')
    workorder_efficiency = fields.Float('Eficiencia de Orden de Trabajo', compute='_compute_workorder_efficiency')
    thirty_daily_efficiency = fields.Char(related='workcenter_id.thirty_daily_efficiency')

    finish_move_line_ids = fields.One2many('sit_tracking_production_produced','sit_mrp_workorder', string='Producido')
    raw_move_line_ids  = fields.One2many('sit_tracking_production_consumed','sit_mrp_workorder', string='Consumido')

    sit_qty_started = fields.Float('Started Quantity')
    previous_rec = fields.Many2one('mrp.workcenter.productivity', 'Previous Record', readonly=True)
    sit_time_begin = fields.Float('Tiempo inicial de fabricación unitario')
    sit_date_begin = fields.Datetime(string='Fecha de inicio de tarea')
    time_id_inicial = fields.Integer(string='ID tiempo inicial')



    def button_start(self, qty_started=None, previous_rec=None):
        _logger.info("SIT button_start qty_started =%s", qty_started)
        _logger.info("SIT button_start previous_rec =%s", previous_rec)
        self.ensure_one()
        # 判断可开工数量 （计划开工-生产中-已完工） qty_remaining 计划生产数量 qty_operation_wip 生产中 qty_operation_comp 已完工
        _logger.info("SIT button_start workorder.qty_remaining =%s", self.qty_remaining)

        if self.qty_operation_avail <= 0 and self.qty_operation_wip <= 0:
            raise UserError(_("No Available to Start Quantity. Planned production Quantity: %s, In-Progress "
                              "Quantity: %s, Completed Quantity: %s." % (self.query_comp_qty(),
                                                                         self.qty_operation_wip,
                                                                         self.qty_operation_comp)))
        _logger.info("SIT button_start0 quantity_done =%s", self.move_raw_ids[0].quantity_done)
        
        # super().button_start()
        self.sit_button_start()
        _logger.info("SIT button_start_0 qty_remaining =%s", self.qty_remaining)
        _logger.info("SIT button_start_0 qty_started =%s", qty_started)

        if qty_started is not None:

            qty_wip = self.qty_operation_wip + (0 if previous_rec else qty_started)
            _logger.info("SIT button_start_1_0_1 qty_wip =%s", qty_wip)

            self.qty_operation_wip = qty_wip if qty_wip <= self.qty_remaining else self.qty_remaining
            _logger.info("SIT button_start_1 qty_operation_wip =%s", self.qty_operation_wip)
            _logger.info("SIT button_start_1 qty_remaining =%s", self.qty_remaining)
            
            domain = [('workorder_id', '=', self.id), ('date_end', '=', False),
                      ('user_id', '=', self.env.user.id)]
            productivity = self.env['mrp.workcenter.productivity'].search(domain, limit=1, order='date_start ASC')

            _logger.info("SIT button_start_2 qty_remaining =%s", self.qty_remaining)
            
                        
            productivity.qty_started = qty_started

            _logger.info("SIT button_start_3 qty_remaining =%s", self.qty_remaining)
                        
            if previous_rec is not None or previous_rec:
                previous_rec.next_rec = productivity.id


        _logger.info("SIT button_start1 quantity_done =%s", self.move_raw_ids[0].quantity_done)




    def _should_start_timer(self):
        return True


    def sit_button_start(self):
        self.ensure_one()
        _logger.info("SIT sit_button_start_0 quantity_done =%s", self.move_raw_ids[0].quantity_done)

        if any(not time.date_end for time in self.time_ids.filtered(lambda t: t.user_id.id == self.env.user.id)):
            return True
        # As button_start is automatically called in the new view
        if self.state in ('done', 'cancel'):
            return True
        _logger.info("SIT sit_button_start_0_0 quantity_done =%s", self.move_raw_ids[0].quantity_done)

        if self.production_id.state != 'progress':
            self.production_id.write({
                'date_start': datetime.now(),
            })
        _logger.info("SIT sit_button_start_0_1 quantity_done =%s", self.move_raw_ids[0].quantity_done)
        _logger.info("SIT sit_button_start_0_1 product_tracking =%s", self.product_tracking)


        # new_qty = float_round((mo.qty_producing - mo.qty_produced) * self.unit_factor, precision_rounding=self.product_uom.rounding)


        if self.product_tracking == 'serial' and self.qty_producing == 0:
            self.qty_producing = 1.0
        elif self.qty_producing == 0:
            self.qty_producing = 1.0
            # self.qty_remaining
        _logger.info("SIT sit_button_start_0_2 quantity_done =%s", self.move_raw_ids[0].quantity_done)

        if self._should_start_timer():
            self.env['mrp.workcenter.productivity'].create(
                self._prepare_timeline_vals(self.duration, datetime.now())
            )
        _logger.info("SIT sit_button_start_0_3 quantity_done =%s", self.move_raw_ids[0].quantity_done)

        if self.state == 'progress':
            return True
        start_date = datetime.now()
        vals = {
            'state': 'progress',
            'date_start': start_date,
        }
        if not self.leave_id:
            leave = self.env['resource.calendar.leaves'].create({
                'name': self.display_name,
                'calendar_id': self.workcenter_id.resource_calendar_id.id,
                'date_from': start_date,
                'date_to': start_date + relativedelta(minutes=self.duration_expected),
                'resource_id': self.workcenter_id.resource_id.id,
                'time_type': 'other'
            })
            vals['leave_id'] = leave.id
            _logger.info("SIT sit_button_start_1_0 quantity_done =%s", self.move_raw_ids[0].quantity_done)
            _logger.info("SIT sit_button_start_1_0 qty_operation_avail =%s", self.qty_operation_avail)

            return self.write(vals)
        else:
            if not self.date_planned_start or self.date_planned_start > start_date:
                vals['date_planned_start'] = start_date
                vals['date_planned_finished'] = self._calculate_date_planned_finished(start_date)
            if self.date_planned_finished and self.date_planned_finished < start_date:
                vals['date_planned_finished'] = start_date
            _logger.info("SIT sit_button_start_1_1 quantity_done =%s", self.move_raw_ids[0].quantity_done)
            _logger.info("SIT sit_button_start_1_1 qty_operation_avail =%s", self.qty_operation_avail)

            return self.with_context(bypass_duration_calculation=True).write(vals)








    # def button_finish(self):
    #     self.ensure_one()


    #     super().button_finish()
    #     _logger.info("SIT button_finish super ralizado")
    #     NEW_PRODUCED_PRODUCT = self.count_produced(1, self.id)        
        














    def end_previous(self, doall=False, Part_omp=False):
        """
        Args:
            doall: inherit
            Part_omp: Indicates that the current reporting is completed, and there are no further tasks. Otherwise,
            it will be marked as paused, and when the next operation starts, the last end information will be read
            to record continuous working time information.
        Returns:

        """

        _logger.info("SIT end_previous doall=%s, Part_omp=%s", doall, Part_omp)
        MENSAJE= "SIT end_previous doall=" + str(doall) + ", Part_omp=" + str(Part_omp)


        if not Part_omp:
            timeline_obj = self.env['mrp.workcenter.productivity']
            domain = [('workorder_id', 'in', self.ids), ('date_end', '=', False)]
            if not doall:
                domain.append(('user_id', '=', self.env.user.id))
            for timeline in timeline_obj.search(domain, limit=None if doall else 1):
                if doall:
                    timeline.action_type = 'block'
                else:
                    timeline.action_type = 'pause'
                
            
            MENSAJE = "domain= "+ str(domain) +  ", action_type =" 
            # raise UserError(_( MENSAJE))
       
        # _logger.info("SIT end_previous0 quantity_done =%s", self.move_raw_ids[0].quantity_done)

        super().end_previous(doall)
        if  Part_omp or doall:
            _logger.info("SIT end_previous super ralizado")
            # _logger.info("SIT end_previous1 quantity_done =%s", self.move_raw_ids[0].quantity_done)
            CALCULO_CONSUMED = self.count_total_consumed()
            # raise UserError(_( MENSAJE))                    
            NEW_PRODUCED_PRODUCT = self.count_produced(1, self.id, CALCULO_CONSUMED)
        
        self.qty_producing = self.qty_operation_comp
        if doall:
            componentes = self.production_id.move_raw_ids
            proction_id = self.production_id.move_raw_ids





    def end_previous_1(self, doall=False):
        """
        @param: doall:  This will close all open time lines on the open work orders when doall = True, otherwise
        only the one of the current user
        """
        _logger.info("SIT end_previous_1_0 quantity_done =%s", self.move_raw_ids[0].quantity_done)

        # TDE CLEANME
        timeline_obj = self.env['mrp.workcenter.productivity']
        domain = [('workorder_id', 'in', self.ids), ('date_end', '=', False)]
        if not doall:
            domain.append(('user_id', '=', self.env.user.id))
        not_productive_timelines = timeline_obj.browse()
        for timeline in timeline_obj.search(domain, limit=None if doall else 1):
            wo = timeline.workorder_id
            if wo.duration_expected <= wo.duration:
                if timeline.loss_type == 'productive':
                    not_productive_timelines += timeline
                timeline.write({'date_end': fields.Datetime.now()})
            else:
                maxdate = fields.Datetime.from_string(timeline.date_start) + relativedelta(minutes=wo.duration_expected - wo.duration)
                enddate = datetime.now()
                if maxdate > enddate:
                    timeline.write({'date_end': enddate})
                else:
                    timeline.write({'date_end': maxdate})
                    not_productive_timelines += timeline.copy({'date_start': maxdate, 'date_end': enddate})
        if not_productive_timelines:
            loss_id = self.env['mrp.workcenter.productivity.loss'].search([('loss_type', '=', 'performance')], limit=1)
            if not len(loss_id):
                raise UserError(_("You need to define at least one unactive productivity loss in the category 'Performance'. Create one from the Manufacturing app, menu: Configuration / Productivity Losses."))
            not_productive_timelines.write({'loss_id': loss_id.id})
        _logger.info("SIT end_previous_1_1 quantity_done =%s", self.move_raw_ids[0].quantity_done)

        return True


    def button_reporting_start_1(self):
        self.ensure_one()
        return self.start_action(action_type='start')

    def start_action(self,action_type):
        _logger.info("SIT start_action self.qty_remaining =%s", self.qty_remaining)

        domain = [('workorder_id', '=', self.id), ('user_id', '=', self.env.user.id)]
        domain += [('action_type', 'in', ['block', 'pause']), ('next_rec', '=', False)]
        _logger.info("SIT start_action  domain =%s", domain)
        productivity = self.env['mrp.workcenter.productivity'].sudo().search(domain, limit=1)
        tiempo = self.env['mrp.workcenter.productivity'].sudo().search_read(domain, limit=1)
        _logger.info("SIT  start_action tiempo =%s ", tiempo)

        #Obtiene Insumos
        insumos = self.move_raw_ids[0]

        insumo_s = []
        for insumo in insumos:
            insumo_s.append(insumo)
        MENSAJE = "Insumo_s =" + str(insumos.quantity_done)
        _logger.info("SIT start_action =%s", MENSAJE)
        # raise UserError(MENSAJE)
        # qty_started = 1
        qty_started =  self.production_id.bom_id.product_qty
        if productivity and productivity.qty_started > 0:
            self.previous_rec = productivity.id
            _logger.info("SIT  start_action previous_rec =%s ", self.previous_rec)
        else:
            self.previous_rec = productivity

                

        if qty_started <= 0:
            raise UserError(_("Required to Fill in the Started Quantity. "))
        elif qty_started > self.qty_operation_avail and not self.previous_rec:
            raise UserError(_("Exceeding the Available to Start Quantity. Planned production Quantity: %s, In-Progress "
                              "Quantity: %s, Completed Quantity: %s." % (self.workorder_id.qty_remaining,
                                                                         self.workorder_id.qty_operation_wip,
                                                                         self.workorder_id.qty_operation_comp)))
        # qty_started = float_round(qty_started, precision_rounding=self.workorder_id.production_id.product_uom_id.rounding)
        _logger.info("SIT start_action  qty_started=%s - previous_rec =%s",  qty_started, self.previous_rec )
        if self.qty_operation_wip == 0.0:
            self.sit_time_begin = self.duration
            self.sit_date_begin = fields.Datetime.now()
            
            # ultimo_tiempo_relacionado = self.time_ids.search([], order='id desc', limit=1)
            # ultimo_tiempo_relacionado_action_type = ultimo_tiempo_relacionado.action_type
            # _logger.info("SIT -xxxx---count_total_consumed ultimo_tiempo_relacionado =%s   (%s)", ultimo_tiempo_relacionado, ultimo_tiempo_relacionado_action_type)


            # self.time_id_inicial = 
        self.button_start(qty_started, self.previous_rec)
        # INSUMOS CONSUMIDOS 
        insumos = self.move_raw_ids[0]
        MENSAJE = "Insumo_s quantity_done =" + str(insumos.quantity_done)
        _logger.info("SIT start_action =%s", MENSAJE)
        ultimo_tiempo_relacionado = self.time_ids.search([], order='id desc', limit=1)
        _logger.info("SIT -----count_total_consumed ultimo_tiempo_relacionado =%s   (%s)", ultimo_tiempo_relacionado, ultimo_tiempo_relacionado.action_type)
        
        tempos_relacionado = self.time_ids.search([('date_start', '>', self.sit_date_begin)])
        MENSAJE = "ultimo_tiempo_relacionado=" + str(ultimo_tiempo_relacionado) + "--> " + str(ultimo_tiempo_relacionado.action_type) + "--> " + str(ultimo_tiempo_relacionado.date_start)  + "--> " + str(tempos_relacionado) + "--> " + str(len(tempos_relacionado)) 
        # raise UserError(_( MENSAJE))                    
        if ultimo_tiempo_relacionado.action_type == False and len(tempos_relacionado) == 1:
            NEW_CONSUMED_PRODUCT = self.count_consumed(self.qty_operation_wip, self.id)        

    def button_reporting_start(self):
        self.ensure_one()
        return self.open_reporting_wizard(action_type='start')


    def button_reporting_finish_1(self):
        self.ensure_one()
        # return self.open_reporting_wizard(action_type='finish')
        return self.finish_action(action_type='finish')

    def finish_action(self, action_type):

        timeline_obj = self.env['mrp.workcenter.productivity']
        comp_items = []
        # comp = self.qty_completed if self.qty_completed > 0 else 0
        # comp = self.qty_operation_comp if self.qty_operation_comp > 0 else 0
        comp = self.production_id.bom_id.product_qty
        # comp = 1
        _logger.info("SIT finish_action_1 comp =%s", comp)

        for workorder in self:
            _logger.info("SIT finish_action workorder.qty_remaining =%s", workorder.qty_remaining)
            comp = float_round(comp, precision_rounding=self.production_id.product_uom_id.rounding)
            domain = [('workorder_id', '=', self.id), ('date_end', '=', False),
                      ('user_id', '=', self.env.user.id)]
            _logger.info("SIT  finish_action domain =%s ", domain)

            if comp is not None:
                tiempo = timeline_obj.search_read(domain, limit=1)
                _logger.info("SIT  finish_action tiempo =%s ", tiempo)
                for timeline in timeline_obj.search(domain, limit=1):
                    _logger.info("SIT timeline=%s", timeline)
                    if timeline.qty_started >= comp:
                        timeline.qty_completed = comp
                        timeline.action_type = 'finish'
                        # CONTABILIZAR producto terminado
                        _logger.info("SIT workder.id =%s", workorder.id)
                        _logger.info("SIT POST workder.id =%s", workorder.id)
                        qty_wip = workorder.qty_operation_wip - timeline.qty_started
                        workorder.qty_operation_wip = qty_wip if qty_wip > 0 else 0
                        workorder.qty_operation_comp += comp

                        
                    else:
                        raise UserError(_("The completed quantity cannot be greater than the started quantity."))
                    if workorder.qty_remaining > workorder.qty_operation_comp:
                        _logger.info("SIT workorder.qty_remaining =%s , workorder.qty_operation_comp =%s",workorder.qty_remaining , workorder.qty_operation_comp)
                        workorder.end_previous(Part_omp=True)
                        _logger.info("SIT end_previous realizado")
                    else:
                        tiempo_inicial = self.sit_time_begin
                        workorder.button_finish()
                        _logger.info("SIT button_finish realizado")


    def count_total_consumed(self):
        ultimo_registro_relacionado = self.raw_move_line_ids.search([], order='id desc', limit=1)
        ultimo_tiempo_relacionado = self.time_ids.search([], order='id desc', limit=1)
        ultimo_tiempo_relacionado_action_type = ultimo_tiempo_relacionado.action_type
        _logger.info("SIT -----count_total_consumed ultimo_registro_relacionado =%s", ultimo_registro_relacionado)
        _logger.info("SIT -----count_total_consumed ultimo_tiempo_relacionado =%s   (%s) date_start(%s)", ultimo_tiempo_relacionado, ultimo_tiempo_relacionado_action_type, ultimo_tiempo_relacionado.date_start)
        if ultimo_tiempo_relacionado_action_type in ['block','finish']:
            _logger.info("SIT -----count_total_consumed ultimo_tiempo_relacionado CALCULANDO TIEMPO TOTAL=%s   (%s)", ultimo_tiempo_relacionado, ultimo_tiempo_relacionado_action_type)
            # primer_tiempo_relacionado = self.time_ids.search([('date_start','in',self.sit_date_begin)] ) 
            # _logger.info("SIT -----count_total_consumed primer_tiempo_relacionado =%s   (%s)", self.sit_date_begin, primer_tiempo_relacionado)
            tempos_relacionado = self.time_ids.search([('date_start', '>', self.sit_date_begin)])
            tiempo_total = 0.0
            for tiempo in tempos_relacionado:
                tiempo_total += tiempo.duration


            # tempos_relacionado = self.time_ids.search([('id','>',primer_tiempo_relacionado)])
            _logger.info("SIT -----count_total_consumed tempos_relacionado CALCULANDO TIEMPO TOTAL=%s   (%s)", tempos_relacionado, tiempo_total)
            ultimo_registro_relacionado.blocktime_duration = tiempo_total
            return tiempo_total
        else:
            return
        # ultimo_registro_relacionado = mi_modelo.registros_relacionados.search([], order='id desc', limit=1)



    def count_consumed(self, comp, workorder):

        sit_mrp_workorder = workorder
        date = self.sit_date_begin
        product_id = self.product_id.id
        # 'lot_id': NUEVA_FACTURA.id,
        qty_done = comp
        state = 'confirmed'
        blocktime_duration = self.duration - self.sit_time_begin

        componentes = []
        subcomponentes = []
        for componente in self.production_id.bom_id.bom_line_ids:
            producto_id = componente.product_id
            qty  = componente.product_qty
            VALORES_LINEA =  {
                    'sit_mrp_workorder': sit_mrp_workorder,
                    'date': date,
                    'product_id': producto_id.id,
                    # 'lot_id': NUEVA_FACTURA.id,
                    'qty_done': qty,
                    # 'qty_done': comp * qty,
                    'state': 'confirmed',
                    'blocktime_duration': self.duration - self.sit_time_begin,

                }
            MENSAJE = "VALORES componentes=" + str(VALORES_LINEA) + ", duration =" + str(self.duration) + ", timebegin=" + str(self.sit_time_begin)
            _logger.info("SIT MENSAJE =%s", MENSAJE)
            # raise UserError(_(MENSAJE))               

            self.env['sit_tracking_production_consumed'].create(VALORES_LINEA)






    def count_produced(self, comp, workorder,tiempo_consumido):

        sit_mrp_workorder = workorder
        date = self.sit_date_begin
        product_id = self.product_id.id
        # 'lot_id': NUEVA_FACTURA.id,
        qty_done = comp
        state = 'confirmed'
        blocktime_duration = self.duration - self.sit_time_begin

        componentes = []
        subcomponentes = []

        VALORES_LINEA =  {
                'sit_mrp_workorder': workorder,
                'date': self.sit_date_begin,
                'product_id': self.product_id.id,
                # 'lot_id': NUEVA_FACTURA.id,
                'qty_done': comp,
                'state': 'confirmed',
                'blocktime_duration': tiempo_consumido,

            }
        MENSAJE = "VALORES=" + str(VALORES_LINEA) + ", duration =" + str(self.duration) + ", timebegin=" + str(self.sit_time_begin)
        _logger.info("SIT MENSAJE =%s", MENSAJE)
        # raise UserError(_(MENSAJE))               



        self.env['sit_tracking_production_produced'].create(VALORES_LINEA)

        for componente in self.production_id.bom_id.byproduct_ids:

            producto_id = componente.product_id
            qty  = componente.product_qty
            VALORES_LINEA =  {
                    'sit_mrp_workorder': sit_mrp_workorder,
                    'date': date,
                    'product_id': producto_id.id,
                    # 'lot_id': NUEVA_FACTURA.id,
                    'qty_done': comp * qty,
                    'state': 'confirmed',
                    # 'blocktime_duration': self.duration - self.sit_time_begin,
                    'blocktime_duration': tiempo_consumido,

                }
            MENSAJE = "VALORES componentes=" + str(VALORES_LINEA) + ", duration =" + str(self.duration) + ", timebegin=" + str(self.sit_time_begin)
            _logger.info("SIT MENSAJE =%s", MENSAJE)
            # raise UserError(_(MENSAJE))               

            self.env['sit_tracking_production_produced'].create(VALORES_LINEA)








    def button_reporting_finish(self):
        self.ensure_one()
        return self.open_reporting_wizard(action_type='finish')

    # def button_pending_1(self):
    #     self.ensure_one()
    #     _logger.info("SIT button_pending_1 button_pending_1 =%s", self)
    #     # return self.start_action(action_type='start')


    def button_pending_1(self):
        self.end_previous()
        return True
    # def button_pending(self):
    #     self.end_previous()
    #     return True



    def button_unblock_1(self):
        self.ensure_one()
        _logger.info("SIT button_unblock_1 button_unblock_1 =%s", self)
        # return self.start_action(action_type='start')




    def open_reporting_wizard(self, action_type):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Operation ' + action_type),
            'res_model': 'mrp.reporting.operation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id,
                        'action_type': action_type},
            'views': [[False, 'form']]
        }

    def open_workorder_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Open Workorder Reporting Interface'),
            'res_model': 'mrp.open.workorder.wizard',
            'view_mode': 'form',
            'target': 'new',
            'views': [[False, 'form']]
        }

    def action_mrp_workorder_view_form_tablet(self):
        view_id = self.env.ref('leas_mes_process_reporting.mrp_workorder_view_form_tablet').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Operation Reporting'),
            'res_model': 'mrp.workorder',
            'target': 'fullscreen',
            'res_id': self.id,
            'views': [[view_id, 'form']],
            'view_id': view_id,
            'flags': {
                'withControlPanel': False,
                'form_view_initial_mode': 'edit',
            },
        }

    def _start_nextworkorder(self):
        super()._start_nextworkorder()
        is_first = self.env['mrp.workorder'].sudo().search([('next_work_order_id', '=', self.id)])
        if self.qty_operation_comp == 0 and is_first:
            return
        next_order = self.next_work_order_id
        parallel_orders = []
        while next_order and not next_order.reporting_point:
            parallel_orders.append(next_order)
            next_order = next_order.next_work_order_id
        parallel_orders.append(next_order)
        for order in parallel_orders:
            if order.state == 'pending' and order.qty_operation_avail > 0:
                order.state = 'ready' if order.production_availability == 'assigned' else 'waiting'

    @api.constrains('qty_operation_wip', 'qty_operation_comp')
    def _check_qty_operation(self):
        for wo in self:
            if wo.state in ['done', 'cancel']:
                raise UserError(_(u"Not allowed to modify the completion quantity of completed work orders."))
            _logger.info("SIT _check_qty_operation_0 qty_operation_avail =%s", wo.qty_operation_avail)
            ref_qty = wo.query_comp_qty()
            _logger.info("SIT ref_qty =%s", ref_qty)
            _logger.info("SIT _check_qty_operation qty_operation_avail =%s", wo.qty_operation_avail)
            _logger.info("SIT qty_operation_wip =%s", wo.qty_operation_wip)
            _logger.info("SIT qty_operation_comp =%s", wo.qty_operation_comp)

            if wo.qty_operation_wip > ref_qty or wo.qty_operation_comp > ref_qty or \
                    wo.qty_operation_wip > (ref_qty - wo.qty_operation_comp):
                raise UserError(_(u"Cannot Exceed Work Order Quantity."))
            if wo.qty_operation_wip < 0 or wo.qty_operation_comp < 0:
                raise UserError(_(u"Not Support Negative Numbers."))
            par_orders = self.browse()
            next_order = wo.next_work_order_id
            _logger.info("SIT self =%s", self)
            _logger.info("SIT par_orders =%s", par_orders)
            _logger.info("SIT next_order =%s", next_order)
            _logger.info("SIT next_order.next_work_order_id =%s", next_order.next_work_order_id)

            if not wo.reporting_point:
                continue
            while next_order and not next_order.reporting_point:
                par_orders |= next_order
                next_order = next_order.next_work_order_id
            par_orders |= next_order
            # max_par_op_qty_0 = max(x.qty_operation_wip + x.qty_operation_comp for x in par_orders)
            if par_orders:
                max_par_op_qty = (x.qty_operation_wip + x.qty_operation_comp for x in par_orders)
            else:
                max_par_op_qty = 0
            _logger.info("SIT max_par_op_qty =%s", max_par_op_qty)


            if wo.qty_operation_comp < max_par_op_qty:
                raise UserError(_(u"Subsequent operations have started, and the completion quantity "
                                  u"cannot be lower than %s." % str(max_par_op_qty)))

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].next_by_code('mrp.workorder') or '/'
        res = super().create(values)
        return res

    def action_return_view_workorder(self):
        '''
        Return to List View
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('mrp.mrp_workorder_todo')
        context = dict(self.env.context)
        action_context = ast.literal_eval(action['context'])
        context.update(action_context)
        action['context'] = context
        action['target'] = 'main'

        return action

    @api.depends('qty_remaining', 'qty_operation_wip', 'qty_operation_comp')
    def _compute_Proc_chart_data(self):
        name_qty_operation_wip = self._fields['qty_operation_wip'].string
        name_qty_operation_comp = self._fields['qty_operation_comp'].string
        name_qty_operation_avail = self._fields['qty_operation_avail'].string
        for rec in self:
            chart_data = []
            for wo in rec.production_id.workorder_ids:
                chart_data.append({'category': wo.name,
                                   name_qty_operation_avail: wo.qty_operation_avail,
                                   name_qty_operation_wip: wo.qty_operation_wip,
                                   name_qty_operation_comp: wo.qty_operation_comp})
            rec.mo_Proc_chart_data = json.dumps(chart_data, indent=4)
            chart_data = [
                {'value': rec.qty_operation_avail, 'name': name_qty_operation_avail},
                {'value': rec.qty_operation_wip, 'name': name_qty_operation_wip},
                {'value': rec.qty_operation_comp, 'name': name_qty_operation_comp},
            ]
            rec.wo_Proc_chart_data = json.dumps(chart_data, indent=4)

    @api.depends('time_ids')
    def _compute_workorder_efficiency(self):
        for wo in self:
            planned_proc_time = wo.duration_expected / wo.qty_production
            done_times = [time for time in wo.time_ids if time.action_type == 'finish']
            comp_qty = 0
            comp_duration = 0
            for time in done_times:
                comp_qty = comp_qty + time.qty_completed
                proc_records = time.get_processing_time_recs()
                comp_duration += sum(proc_records.mapped('duration'))
            if comp_duration:
                wo.workorder_efficiency = round(comp_qty * planned_proc_time / comp_duration * 100, 2)
            else:
                wo.workorder_efficiency = 0
            _logger.info("SIT _compute_workorder_efficiency workorder_efficiency=%s", wo.workorder_efficiency)

    @api.depends('time_ids')
    def _compute_workorder_efficiency(self):
        for wo in self:
            planned_proc_time = wo.duration_expected / wo.qty_production
            done_times = [time for time in wo.time_ids if time.action_type == 'finish']
            comp_qty = 0
            comp_duration = 0
            for time in done_times:
                comp_qty = comp_qty + time.qty_completed
                proc_records = time.get_processing_time_recs()
                comp_duration += sum(proc_records.mapped('duration'))
            if comp_duration:
                wo.workorder_efficiency = round(comp_qty * planned_proc_time / comp_duration * 100, 2)
            else:
                wo.workorder_efficiency = 0
            _logger.info("SIT 2 _compute_workorder_efficiency workorder_efficiency=%s", wo.workorder_efficiency)

    @api.depends('qty_remaining', 'qty_operation_wip', 'qty_operation_comp')
    def _compute_qty_operation_avail(self):
        for rec in self:
            prev_comp_qty = rec.query_comp_qty()
            _logger.info("SIT _compute_qty_operation_avail prev_comp_qty =%s", prev_comp_qty)
            _logger.info("SIT _compute_qty_operation_avail qty_operation_avail =%s", rec.qty_operation_avail)
            
            rec.qty_operation_avail = prev_comp_qty - rec.qty_operation_wip - rec.qty_operation_comp

    def query_comp_qty(self):
        self.ensure_one()
        prev_rec = self.search([('next_work_order_id', '=', self.id)], limit=1)
        _logger.info("SIT query_comp_qty prev_rec =%s", prev_rec)
        _logger.info("SIT query_comp_qty prev_rec.reporting_point =%s", prev_rec.reporting_point)
        _logger.info("SIT query_comp_qty prev_rec.state =%s", prev_rec.state)

        if prev_rec:
            if prev_rec.reporting_point:
                return prev_rec.qty_operation_comp
            else:
                return prev_rec.query_comp_qty()
        else:
            if self.state == 'done':
                return self.qty_operation_comp
            else:
                _logger.info("SIT __________query_comp_qty self.qty_produced =%s", self.qty_produced)
                _logger.info("SIT __________query_comp_qty self.qty_production =%s", self.qty_production)
                # _logger.info("SIT __________query_comp_qty self.move_raw_ids.quantity_done =%s", self.move_raw_ids.quantity_done)

                return self.qty_produced or self.qty_production 
            # or self.qty_produc ing 
