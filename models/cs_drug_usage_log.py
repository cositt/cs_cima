from odoo import models, fields


class DrugUsageLog(models.Model):
    _name = 'cs.drug.usage.log'
    _description = 'Registro de Uso de Medicamentos'
    _order = 'date desc'

    drug_id = fields.Many2one(
        'cs.drug.catalog',
        string='Medicamento',
        required=True,
        ondelete='cascade',
        index=True,
    )
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today,
        index=True,
    )
    usage_type = fields.Selection([
        ('prescription', 'Prescripción'),
        ('analgesia', 'Analgesia'),
        ('prn_rescue', 'Rescate PRN'),
        ('admission', 'Ingreso'),
    ], string='Tipo de Uso', required=True)

    resident_id = fields.Many2one(
        'cs.resident',
        string='Residente',
        ondelete='set null',
    )
