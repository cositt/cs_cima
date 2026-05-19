from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CimaImportWizard(models.TransientModel):
    _name = 'cs.cima.import.wizard'
    _description = 'Importar Medicamentos desde CIMA (AEMPS)'

    query = fields.Char(string='Buscar en CIMA')
    line_ids = fields.One2many('cs.cima.import.line', 'wizard_id', string='Resultados')
    result_count = fields.Integer(compute='_compute_result_count')

    @api.depends('line_ids')
    def _compute_result_count(self):
        for rec in self:
            rec.result_count = len(rec.line_ids)

    def action_search(self):
        self.ensure_one()
        if not self.query or len(self.query) < 2:
            raise UserError(_('Escribe al menos 2 caracteres para buscar.'))

        results = self.env['cs.cima.api.service'].search_drugs(self.query)
        self.line_ids.unlink()

        existing_nregistros = set(
            self.env['cs.drug.catalog'].search([]).mapped('cima_nregistro')
        )

        lines = []
        for r in results[:30]:
            estado = r.get('estado') or {}
            market_status = 'deleted' if (estado.get('rev') or estado.get('susp')) else 'available'
            nregistro = str(r.get('nregistro', ''))
            lines.append({
                'wizard_id': self.id,
                'nregistro': nregistro,
                'nombre': r.get('nombre', ''),
                'labtitular': r.get('labtitular', ''),
                'market_status': market_status,
                'already_exists': nregistro in existing_nregistros,
                'selected': False,
            })

        self.env['cs.cima.import.line'].create(lines)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cs.cima.import.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_import_selected(self):
        self.ensure_one()
        selected = self.line_ids.filtered('selected')
        if not selected:
            raise UserError(_('Selecciona al menos un medicamento para importar.'))

        service = self.env['cs.cima.api.service']
        imported_ids = []
        errors = []

        for line in selected:
            try:
                drug_id = service.get_or_create_catalog(line.nregistro)
                imported_ids.append(drug_id)
            except Exception as e:
                errors.append(f'{line.nombre}: {e}')

        if errors and not imported_ids:
            raise UserError(_('No se pudo importar ningún medicamento:\n') + '\n'.join(errors))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Medicamentos Importados'),
            'res_model': 'cs.drug.catalog',
            'view_mode': 'list,form',
            'domain': [('id', 'in', imported_ids)],
        }


class CimaImportLine(models.TransientModel):
    _name = 'cs.cima.import.line'
    _description = 'Resultado de búsqueda CIMA'
    _order = 'nombre'

    wizard_id = fields.Many2one('cs.cima.import.wizard', required=True, ondelete='cascade')
    nregistro = fields.Char(string='Nº Registro', readonly=True)
    nombre = fields.Char(string='Nombre', readonly=True)
    labtitular = fields.Char(string='Laboratorio', readonly=True)
    market_status = fields.Selection([
        ('available', 'Comercializado'),
        ('deleted', 'Retirado/Suspendido'),
    ], string='Estado', readonly=True)
    already_exists = fields.Boolean(string='Ya en catálogo', readonly=True)
    selected = fields.Boolean(string='Importar')
