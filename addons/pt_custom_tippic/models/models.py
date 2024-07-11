from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Opciones para el campo de selección
    SELECTION_OPTIONS = [
        ('option1', 'Rotación baja'),
        ('option2', 'Rotación media'),
        ('option3', 'Rotación alta'),
    ]

    type_rotation = fields.Selection(SELECTION_OPTIONS, string='Tipo de Rotacion')
    unit_product = fields.Char(string='Unidad de Producto', store=True)
    line_product = fields.Char(string='Linea de Producto', store=True)


class AccountMove(models.Model):
    _inherit = 'account.move'

    guide_remission = fields.Char(string='Guia de remision')
    oc_customer = fields.Char(string='Orden de Compra')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ocs_customer = fields.Char(string='Orden de Compra')

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    date_solicitud = fields.Date(string='Fecha solicitud')
