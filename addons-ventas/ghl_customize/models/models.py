from odoo import fields, models

class SaleOrderCondition(models.Model):
    _name = "sale.condition"
    _description = 'Sale Condition'

    consideration = fields.Char('Consideraciones')
    accion = fields.Char('Accion Requerida')
    area = fields.Selection([
        ('sass', 'SASS'),
        ('qc', 'QC'),
        ('mntto', 'Mntto')
    ], string='Area')
    si_no = fields.Selection([
        ('si', 'Si'),
        ('no', 'No')
    ], string='Si/No')
    
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    attention_customer = fields.Char(string='Atencion')
    ot_warning = fields.Char(string='OT/Aviso')
    so_area = fields.Char(string='Area de Trabajo')
    so_duration = fields.Char(string='Tiempo de Duracion')
    so_description = fields.Char(string='Descripcion del Servicio')
    so_condition = fields.Many2many('sale.condition', string='Conditions')
    so_plazo = fields.Char(string='Plazo de Entrega')

class AccountMove(models.Model):
    _inherit = 'account.move'

    ot_warning = fields.Char(string='OT/Aviso')
    so_area = fields.Char(string='Area de Trabajo')
    so_duration = fields.Char(string='Tiempo de Duracion')
    so_entrega = fields.Date(string='Fecha de Entrega')
    so_plazo = fields.Char(string='Plazo de Entrega')