from odoo import models, fields, api


class PrescriptionLineExtend(models.Model):
    _inherit = 'cs.prescription.line'

    drug_id = fields.Many2one(
        'cs.drug.catalog',
        string='Medicamento (Catálogo)',
        ondelete='set null',
        index=True,
    )
    cima_url = fields.Char(
        string='Ficha CIMA',
        compute='_compute_cima_url',
        store=False,
    )

    @api.depends('drug_id')
    def _compute_cima_url(self):
        for line in self:
            line.cima_url = line.drug_id.cima_url if line.drug_id else False

    @api.onchange('drug_id')
    def _onchange_drug_id(self):
        if self.drug_id:
            self.medication_name = self.drug_id.name
            if self.drug_id.route and not self.via:
                self.via = self.drug_id.route

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.drug_id:
                self.env['cs.drug.usage.log'].create({
                    'drug_id': rec.drug_id.id,
                    'usage_type': 'prescription',
                    'resident_id': rec.prescription_id.resident_id.id,
                })
        return records
