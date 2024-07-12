# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C)  2024.
#    Author      :  Sofia ERP (<http://www.sofiaerp.com>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

import json
import logging
import math
import re
import time
import datetime
import requests

from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date
from odoo.addons.iap.tools import iap_tools
_logger = logging.getLogger(__name__)

DEFAULT_IAP_ENDPOINT = 'https://iap.odoofact.pe'

class Currency(models.Model):
    _inherit = "res.currency"
    _description = "Currency"
    
    rate_pe = fields.Float(compute='_compute_current_rate_pe', string='Peruvian format', digits=(12, 3),
                        help='Currency rate in peruvian format.')
    
    remote_id = fields.Char(string='Remote ID')
    
    def _get_rates_pe(self, company, date):
        self.env['res.currency.rate'].flush(['rate_pe', 'currency_id', 'company_id', 'name'])
        query = """SELECT c.id,
                          COALESCE((SELECT r.rate_pe FROM res_currency_rate r
                                  WHERE r.currency_id = c.id AND r.name <= %s
                                    AND (r.company_id IS NULL OR r.company_id = %s)
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1), 1.0) AS rate_pe
                   FROM res_currency c
                   WHERE c.id IN %s"""
        self._cr.execute(query, (date, company.id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        return currency_rates

    @api.depends('rate_ids.rate')
    def _compute_current_rate_pe(self):
        date = self._context.get('date') or fields.Date.today()
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        # the subquery selects the last rate before 'date' for the given currency/company
        currency_rates = self._get_rates_pe(company, date)
        for currency in self:
            currency.rate_pe = currency_rates.get(currency.id) or 1.0
    
    def rate_connection_call(self):
        self.env['res.currency.rate'].rate_connection()
    
    
    @api.model
    def fetch_exchange_rate_data(self, company, type_consult, currency):
        # ir_params = self.env['ir.config_parameter'].sudo()                                                                       #SIT
        # default_endpoint = self.env['ir.config_parameter'].sudo().get_param('odoofact_iap_endpoint', DEFAULT_IAP_ENDPOINT)       #SIT
        # iap_server_url = ir_params.get_param('l10n_pe_edi_endpoint', default_endpoint)                                           #SIT
        url = "https://api.apis.net.pe/v1/tipo-cambio-sunat"


        # user_token = self.env['iap.account'].get('l10n_pe_data')
        # dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        data = {}
        # params = {
        #     'client_service_token': company.l10n_pe_partner_token,
        #     'remote_id': currency.remote_id,
        #     'account_token': user_token.account_token,
        #     'doc_number': '',
        #     'type_consult': type_consult,
        #     'currency': currency.name,
        #     'company_name': company.name,
        #     'phone': company.phone,
        #     'email': company.email,
        #     'service': 'partner',
        #     'company_image': company.logo.decode('utf-8'),
        #     'number': company.vat,
        #     'dbuuid': dbuuid,
        # }
        # rate = iap_tools.iap_jsonrpc(iap_server_url + '/iap/get_partner_data', params=params)
        try:
            response = requests.get(url)
            # Verificar si la solicitud fue exitosa (código de estado 200)
            if response.status_code == 200:
                result = response.json()
                MENSAJE= "Respuesta : " + str(data) + " , "  + str(type(result)) + " , " + str(result['compra']) + " , " + str(result['fecha'])
                # raise UserError(_(MENSAJE))
                _logger.info("SIT result1 =%s", result)

                if result:
                    rate = result['venta']
                    data = self.rate_connection(rate, result, company, currency)
                    _logger.info("SIT data1 =%s", data)

                return data                   
            else:
                MENSAJE= "Error en la solicitud. Código de estado: " + str(response.status_code)
                raise UserError(_(MENSAJE))

        except requests.exceptions.RequestException as e:
            MENSAJE= "Error en la solicitud : " + str(e)
            raise UserError(_(MENSAJE))


        if rate:
            result = rate['exchange_rates'][0]
            data = self.rate_connection(rate, result, company, currency)
        return data       
        
    @api.model
    def rate_connection(self, rate, result, company, currency):
        data = {}
        _logger.info("SIT rate_connection rate =%s,result =%s,company =%s,currency =%s", rate,result,company,currency)

        try:
            data['company_id'] = company.id
            _logger.info("SIT try data['company_id'] =%s", data['company_id'])            
            data['currency_id'] = currency.id
            _logger.info("SIT try data['currency_id'] =%s", data['currency_id'])            
            data['name'] = date.today()
            _logger.info("SIT try data['name'] =%s", data['name'])
            # data['rate_pe'] = result.get('venta')
            data['rate_pe'] = rate
            _logger.info("SIT try data['rate_pe'] =%s", data['rate_pe'])
            _logger.info("SIT try data =%s", data)
            rate_line = self.env['res.currency.rate'].search([ ('company_id','=',company.id),('currency_id','=',currency.id),('name','=',date.today())], limit=1)
            _logger.info("SIT rate_line =%s", rate_line)
            if rate_line:
                rate_line.write(data)
            else:
                _logger.info("SIT rate_connection  else  data=%s", data)

                rate_line = self.env['res.currency.rate'].create(data)
                currency.remote_id = result.get('origen', False)
            rate_line.onchange_rate_pe()
        except Exception as e:
            _logger.info("SIT rate_connection  Exception = %s", e)

            data = False
        return data

    @api.model     
    def l10n_pe_exchange_rate_connection(self):
        currency_rate=self.env['res.currency.rate'].search([('name','=',date.today())])
        if not currency_rate:
            for currency in self.search([('name','=','USD')]):
                if currency.name == 'USD':
                    for company in self.env['res.company'].search([]).filtered(lambda r: r.currency_id.name == 'PEN'):
                        if company.l10n_pe_exchange_rate_validation == True:
                            # if company.l10n_pe_partner_token:                 #SIT
                                type_consult = 'exchange_rate_consult'
                                currency = currency
                                return self.fetch_exchange_rate_data(company, type_consult, currency)



    def sit_l10n_pe_exchange_rate_connection(self):
        currency_rate=self.env['res.currency.rate'].search([('name','=',date.today())])
        _logger.info("SIT sit_l10n_pe_exchange_rate_connection currency currency_rate =%s", currency_rate)
        if not currency_rate:
            for currency in self.search([('name','=','USD')]):
                if currency.name == 'USD':
                    for company in self.env['res.company'].search([]).filtered(lambda r: r.currency_id.name == 'PEN'):
                        if company.l10n_pe_exchange_rate_validation == True:
                            # if company.l10n_pe_partner_token:                 #SIT
                                type_consult = 'exchange_rate_consult'
                                currency = currency
                                return self.fetch_exchange_rate_data(company, type_consult, currency)
    


class CurrencyRate(models.Model):
    _inherit = "res.currency.rate"
    _description = "Currency Rate"

    rate_pe = fields.Float(string='Change type',digits=(12, 3), default=1.0, help='Currency rate in peruvian format. Ex: 3.25 when $1 = S/. 3.25')

    @api.onchange('rate_pe')
    def onchange_rate_pe(self):
        if self.rate_pe > 0:
            self.rate = 1 / self.rate_pe
        else:
            raise UserError(_('The amount must be greater than zero'))