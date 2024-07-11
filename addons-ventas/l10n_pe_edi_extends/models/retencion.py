import requests
from odoo import fields, api, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round, html_escape

class ResPartner(models.Model):
    _inherit = 'res.partner'

    pe_retention_percent = fields.Float('Porcentaje de Retencion', default=3.00 , copy=False)
    pe_is_retention = fields.Boolean(String='Retencion', copy=False)


class AccountMove(models.Model):
    _inherit = 'account.move'

    
    pe_is_retention = fields.Boolean(String='Retencion', related='partner_id.pe_is_retention')
    pe_retention_percent = fields.Float('Porcentaje de Retencion', related='partner_id.pe_retention_percent')
    pe_retention_amount = fields.Monetary('Monto de Retencion', store=True , compute='_pe_compute_pe_retention_amount', copy=False,  digits=(16,4))
    pe_retention_percent_dec = fields.Monetary('Monto de Retencion decimal', store=True , compute='_pe_compute_pe_retention_amount', copy=False,  digits=(16,4))

    
    @api.depends('pe_retention_percent','pe_is_retention','amount_total')
    def _pe_compute_pe_retention_amount(self):
        for self in self:
            if self.pe_is_retention:
                self.pe_retention_amount = round(self.amount_total*self.pe_retention_percent/100,4)
                self.pe_retention_percent_dec = self.pe_retention_percent/100
            else:
                self.pe_retention_amount = 0
                self.pe_retention_percent_dec = 0



       
    """def _l10n_pe_edi_get_edi_values(self, invoice):
        res = super(AccountMove, self)._l10n_pe_edi_get_edi_values(invoice)
        res.update({
            'pe_is_retention': invoice.pe_is_retention,
            'pe_retention_percent': invoice.pe_retention_percent/100 if invoice.pe_retention_percent > 0 else 0,
            'pe_retention_amount': invoice.pe_retention_amount,
        })
                       
        
        return res """

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_pe_edi_get_edi_values(self, invoice):

        self.ensure_one()
        price_precision = self.env['decimal.precision'].precision_get('Product Price')

        def format_float(amount, precision=2):
            ''' Helper to format monetary amount as a string with 2 decimal places. '''
            if amount is None or amount is False:
                return None
            return '%.*f' % (precision, amount)

        spot = invoice._l10n_pe_edi_get_spot()
        invoice_date_due_vals_list = []
        first_time = True
        for rec_line in invoice.line_ids.filtered(lambda l: l.account_internal_type=='receivable'):
            amount = rec_line.amount_currency
            if spot and first_time:
                amount -= spot['spot_amount']
            first_time = False
            invoice_date_due_vals_list.append({'amount':  round(round(rec_line.move_id.currency_id.round(amount),2)-(rec_line.move_id.currency_id.round(amount)*round(invoice.pe_retention_percent_dec,2)),2),
                                               'currency_name': rec_line.move_id.currency_id.name,
                                               'date_maturity': rec_line.date_maturity})
                                               
        total_cuotas = sum(item['amount'] for item in invoice_date_due_vals_list)
        
        spot = invoice._l10n_pe_edi_get_spot()
        if not spot:
            total_after_spot = abs(invoice.amount_total)
        
        else:
            total_after_spot = abs(invoice.amount_total) - spot['spot_amount']

        

        values = {
            **invoice._prepare_edi_vals_to_export(),
            'spot': spot,
            'total_after_spot':  total_after_spot, # - invoice.pe_retention_amount,
            'total_cuotas': total_cuotas,
            'PaymentMeansID': invoice._l10n_pe_edi_get_payment_means(),
            'is_refund': invoice.move_type in ('out_refund', 'in_refund'),
            'certificate_date': invoice.invoice_date,
            'price_precision': price_precision,
            'format_float': format_float,
            'invoice_date_due_vals_list': invoice_date_due_vals_list,
        }

        # raise UserError(str('%s y %s' % (invoice.currency_id.round(total_after_spot), invoice_date_due_vals_list )))

        # Invoice lines.
        for line_vals in values['invoice_line_vals_list']:
            line = line_vals['line']
            line_vals['price_unit_type_code'] = '01' if not line.currency_id.is_zero(line_vals['price_unit_after_discount']) else '02'
            line_vals['price_subtotal_unit'] = float_round(line.price_subtotal / line.quantity, precision_digits=price_precision) if line.quantity else 0.0
            line_vals['price_total_unit'] = float_round(line.price_total / line.quantity, precision_digits=price_precision) if line.quantity else 0.0

        # Tax details.
        def grouping_key_generator(tax_values):
            tax = tax_values['tax_id']
            return {
                'l10n_pe_edi_code': tax.tax_group_id.l10n_pe_edi_code,
                'l10n_pe_edi_international_code': tax.l10n_pe_edi_international_code,
                'l10n_pe_edi_tax_code': tax.l10n_pe_edi_tax_code,
            }

        values['tax_details'] = invoice._prepare_edi_tax_details()
        values['tax_details_grouped'] = invoice._prepare_edi_tax_details(grouping_key_generator=grouping_key_generator)

        return values