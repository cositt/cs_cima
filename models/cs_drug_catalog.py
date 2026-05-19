from odoo import models, fields, api

CIMA_PUBLIC_URL = 'https://cima.aemps.es/cima/publico/detalle.html'


class DrugCatalog(models.Model):
    _name = 'cs.drug.catalog'
    _description = 'Catálogo de Medicamentos'
    _inherit = ['mail.thread']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Nombre del Medicamento', required=True, tracking=True)
    active_principles = fields.Char(string='Principios Activos')
    galenical_form = fields.Char(string='Forma Farmacéutica')

    route = fields.Selection([
        ('oral', 'Oral'),
        ('intramuscular', 'Intramuscular'),
        ('intravenosa', 'Intravenosa'),
        ('subcutanea', 'Subcutánea'),
        ('topica', 'Tópica'),
        ('inhalada', 'Inhalada'),
        ('sublingual', 'Sublingual'),
        ('rectal', 'Rectal'),
        ('transdermico', 'Transdérmico'),
        ('other', 'Otro'),
    ], string='Vía de Administración')

    atc_code = fields.Char(string='Código ATC')
    atc_description = fields.Char(string='Descripción ATC')
    laboratory = fields.Char(string='Laboratorio')

    market_status = fields.Selection([
        ('available', 'Comercializado'),
        ('deleted', 'Retirado/Suspendido'),
    ], string='Estado', default='available')

    # Condiciones clínicas de la API CIMA
    prescription_conditions = fields.Char(string='Condiciones de Prescripción')
    requires_prescription = fields.Boolean(string='Requiere Receta')
    affects_driving = fields.Boolean(string='Afecta a la Conducción')
    black_triangle = fields.Boolean(string='Triángulo Negro')
    supply_problem = fields.Boolean(string='Problema de Suministro')

    # Identificadores CIMA (AEMPS)
    cima_nregistro = fields.Char(string='Nº Registro CIMA', index=True)
    cima_url = fields.Char(string='URL Ficha CIMA', compute='_compute_cima_url', store=False)
    last_sync_date = fields.Datetime(string='Última Sincronización CIMA')

    is_center_favorite = fields.Boolean(string='Favorito del Centro', default=False)
    notes = fields.Text(string='Observaciones Internas')

    usage_count = fields.Integer(
        string='Usos en el Centro',
        compute='_compute_usage_count',
        store=False,
    )

    @api.depends('cima_nregistro')
    def _compute_cima_url(self):
        for drug in self:
            if drug.cima_nregistro:
                drug.cima_url = f'{CIMA_PUBLIC_URL}?nregistro={drug.cima_nregistro}'
            else:
                drug.cima_url = False

    @api.depends()
    def _compute_usage_count(self):
        for drug in self:
            drug.usage_count = self.env['cs.drug.usage.log'].search_count([
                ('drug_id', '=', drug.id)
            ])

    def action_view_usage_log(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Usos — {self.name}',
            'res_model': 'cs.drug.usage.log',
            'view_mode': 'list',
            'domain': [('drug_id', '=', self.id)],
            'context': {'default_drug_id': self.id},
        }
