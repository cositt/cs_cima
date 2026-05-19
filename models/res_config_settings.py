from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cima_api_enabled = fields.Boolean(
        string='Activar búsqueda CIMA (AEMPS)',
        config_parameter='cs_cima.cima_api_enabled',
        help='Activa la búsqueda de medicamentos en la base de datos pública de la AEMPS. '
             'No requiere API key ni registro.',
    )
