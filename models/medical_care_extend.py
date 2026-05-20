from odoo import models, fields, api


class MedicalTreatmentLineExtend(models.Model):
    _inherit = 'cs.medical.treatment.line'

    drug_id = fields.Many2one(
        'cs.drug.catalog',
        string='Medicamento (Catálogo)',
        ondelete='set null',
        index=True,
    )

    @api.onchange('drug_id')
    def _onchange_drug_id_treatment_line(self):
        if self.drug_id:
            self.description = self.drug_id.name
            if self.drug_id.route and not self.route:
                self.route = self.drug_id.route

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.drug_id and rec.treatment_id.resident_id:
                self.env['cs.drug.usage.log'].create({
                    'drug_id': rec.drug_id.id,
                    'usage_type': 'prescription',
                    'resident_id': rec.treatment_id.resident_id.id,
                })
        return records


class MedicalPrnRescueExtend(models.Model):
    _inherit = 'cs.medical.prn.rescue'

    drug_id = fields.Many2one(
        'cs.drug.catalog',
        string='Medicamento (Catálogo)',
        ondelete='set null',
        index=True,
    )

    @api.onchange('drug_id')
    def _onchange_drug_id_prn(self):
        if self.drug_id:
            self.medication_name = self.drug_id.name
            if self.drug_id.route and not self.route:
                self.route = self.drug_id.route

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.drug_id:
                self.env['cs.drug.usage.log'].create({
                    'drug_id': rec.drug_id.id,
                    'usage_type': 'prn_rescue',
                    'resident_id': rec.resident_id.id,
                })
        return records


class MedicalAnalgesiaExtend(models.Model):
    _inherit = 'cs.medical.analgesia'

    drug_id = fields.Many2one(
        'cs.drug.catalog',
        string='Medicamento (Catálogo)',
        ondelete='set null',
        index=True,
    )

    @api.onchange('drug_id')
    def _onchange_drug_id_analgesia(self):
        if self.drug_id:
            self.medication_description = self.drug_id.name
            if self.drug_id.route and not self.route:
                self.route = self.drug_id.route

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.drug_id:
                self.env['cs.drug.usage.log'].create({
                    'drug_id': rec.drug_id.id,
                    'usage_type': 'analgesia',
                    'resident_id': rec.resident_id.id,
                })
        return records
