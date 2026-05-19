"""
Tests del servicio CIMA y el catálogo de medicamentos.

Ejecución:
  # Tests unitarios (sin conexión a internet):
  docker exec <odoo_container> python -m pytest /mnt/extra-addons/cs_cima/tests/ -v
  # O desde Odoo test runner:
  docker exec <odoo_container> odoo -d cs_followup_install_test \
      --test-tags=cs_cima --stop-after-init

  # Tests live (requieren conexión):
  docker exec <odoo_container> odoo -d cs_followup_install_test \
      --test-tags=live_api --stop-after-init
"""
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import UserError


# ---------------------------------------------------------------------------
# Tests unitarios (sin llamadas reales a la API)
# ---------------------------------------------------------------------------

@tagged('post_install', '-at_install', 'cs_cima')
class TestCimaServiceUnit(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env['cs.cima.api.service']

    # _map_route ---------------------------------------------------------

    def test_map_route_oral(self):
        self.assertEqual(self.service._map_route([{'nombre': 'VÍA ORAL'}]), 'oral')

    def test_map_route_intramuscular(self):
        self.assertEqual(self.service._map_route([{'nombre': 'VÍA INTRAMUSCULAR'}]), 'intramuscular')

    def test_map_route_intravenosa(self):
        self.assertEqual(self.service._map_route([{'nombre': 'VÍA INTRAVENOSA'}]), 'intravenosa')

    def test_map_route_subcutanea(self):
        self.assertEqual(self.service._map_route([{'nombre': 'VÍA SUBCUTÁNEA'}]), 'subcutanea')

    def test_map_route_topica(self):
        self.assertEqual(self.service._map_route([{'nombre': 'VÍA TÓPICA CUTÁNEA'}]), 'topica')

    def test_map_route_inhalada(self):
        self.assertEqual(self.service._map_route([{'nombre': 'VÍA INHALATORIA'}]), 'inhalada')

    def test_map_route_transdermico(self):
        self.assertEqual(self.service._map_route([{'nombre': 'VÍA TRANSDÉRMICA'}]), 'transdermico')

    def test_map_route_empty_list(self):
        self.assertEqual(self.service._map_route([]), 'oral')

    def test_map_route_unknown_defaults_oral(self):
        self.assertEqual(self.service._map_route([{'nombre': 'VÍA OCULAR'}]), 'oral')

    def test_map_route_none_nombre(self):
        self.assertEqual(self.service._map_route([{'nombre': None}]), 'oral')

    # _map_status --------------------------------------------------------

    def test_map_status_active_only_aut(self):
        estado = {'aut': 1520427996000}
        self.assertEqual(self.service._map_status(estado), 'available')

    def test_map_status_revoked(self):
        estado = {'aut': 1520427996000, 'rev': 1727263325000}
        self.assertEqual(self.service._map_status(estado), 'deleted')

    def test_map_status_suspended(self):
        estado = {'aut': 1520427996000, 'susp': 1620000000000}
        self.assertEqual(self.service._map_status(estado), 'deleted')

    def test_map_status_both_susp_and_rev(self):
        estado = {'aut': 1520427996000, 'susp': 1620000000000, 'rev': 1727263325000}
        self.assertEqual(self.service._map_status(estado), 'deleted')

    def test_map_status_empty_dict(self):
        self.assertEqual(self.service._map_status({}), 'available')

    def test_map_status_none(self):
        self.assertEqual(self.service._map_status(None), 'available')

    # search_drugs — verifica que usa 'comerc' no 'comercc' ---------------

    @patch('requests.get')
    def test_search_drugs_uses_comerc_param(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'resultados': []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        self.service.search_drugs('omeprazol')

        mock_get.assert_called_once()
        params = mock_get.call_args.kwargs.get('params', {})
        self.assertIn('comerc', params, "Debe usar 'comerc', no 'comercc'")
        self.assertNotIn('comercc', params, "El parámetro incorrecto 'comercc' no debe usarse")
        self.assertEqual(params['comerc'], 1)

    @patch('requests.get')
    def test_search_drugs_short_query_skips_api(self, mock_get):
        result = self.service.search_drugs('a')
        self.assertEqual(result, [])
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_search_drugs_empty_query_skips_api(self, mock_get):
        result = self.service.search_drugs('')
        self.assertEqual(result, [])
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_search_drugs_timeout_returns_empty(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout()
        result = self.service.search_drugs('omeprazol')
        self.assertEqual(result, [])

    # get_or_create_catalog -----------------------------------------------

    def _make_details(self, nregistro='99999', nombre='TEST MED 10 MG'):
        return {
            'nregistro': nregistro,
            'nombre': nombre,
            'pactivos': 'TESTINA',
            'labtitular': 'Lab Test S.A.',
            'estado': {'aut': 1520427996000},
            'cpresc': 'Medicamento Sujeto A Prescripción Médica',
            'receta': True,
            'conduc': False,
            'triangulo': False,
            'psum': False,
            'atcs': [
                {'codigo': 'A02B', 'nombre': 'AGENTES ULCERA', 'nivel': 3},
                {'codigo': 'A02BC05', 'nombre': 'Esomeprazol', 'nivel': 5},
            ],
            'principiosActivos': [
                {'id': 1, 'nombre': 'TESTINA', 'cantidad': '10', 'unidad': 'mg', 'orden': 1}
            ],
            'viasAdministracion': [{'id': 48, 'nombre': 'VÍA ORAL'}],
            'formaFarmaceutica': {'id': 1, 'nombre': 'COMPRIMIDO'},
        }

    @patch('requests.get')
    def test_get_or_create_catalog_creates_drug(self, mock_get):
        details = self._make_details()
        mock_resp = MagicMock()
        mock_resp.json.return_value = details
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        drug_id = self.service.get_or_create_catalog('99999')
        self.assertTrue(drug_id)

        drug = self.env['cs.drug.catalog'].browse(drug_id)
        self.assertEqual(drug.name, 'TEST MED 10 MG')
        self.assertEqual(drug.cima_nregistro, '99999')
        self.assertEqual(drug.active_principles, 'TESTINA')
        self.assertEqual(drug.route, 'oral')
        self.assertEqual(drug.market_status, 'available')
        self.assertTrue(drug.requires_prescription)
        self.assertFalse(drug.affects_driving)
        self.assertFalse(drug.black_triangle)
        self.assertFalse(drug.supply_problem)

    @patch('requests.get')
    def test_get_or_create_catalog_uses_most_specific_atc(self, mock_get):
        """El ATC almacenado debe ser el nivel más específico (último en la lista)."""
        details = self._make_details()
        mock_resp = MagicMock()
        mock_resp.json.return_value = details
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        drug_id = self.service.get_or_create_catalog('99999')
        drug = self.env['cs.drug.catalog'].browse(drug_id)

        # Debe usar el ATC de nivel 5, no el de nivel 3
        self.assertEqual(drug.atc_code, 'A02BC05')
        self.assertEqual(drug.atc_description, 'Esomeprazol')

    @patch('requests.get')
    def test_get_or_create_catalog_returns_existing(self, mock_get):
        existing = self.env['cs.drug.catalog'].create({
            'name': 'TEST DRUG EXISTING',
            'cima_nregistro': '88888',
        })

        result_id = self.service.get_or_create_catalog('88888')
        self.assertEqual(result_id, existing.id)
        mock_get.assert_not_called()

    def test_get_or_create_catalog_uses_prefetched_details(self):
        """Si se pasan details, NO debe llamar a la API."""
        details = self._make_details(nregistro='77777', nombre='PREFETCHED DRUG 5 MG')

        with patch('requests.get') as mock_get:
            drug_id = self.service.get_or_create_catalog('77777', details=details)
            mock_get.assert_not_called()

        drug = self.env['cs.drug.catalog'].browse(drug_id)
        self.assertEqual(drug.name, 'PREFETCHED DRUG 5 MG')
        self.assertEqual(drug.cima_nregistro, '77777')

    @patch('requests.get')
    def test_get_or_create_catalog_raises_if_api_returns_empty(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        with self.assertRaises(UserError):
            self.service.get_or_create_catalog('00000')

    # _build_catalog_vals -------------------------------------------------

    def test_build_catalog_vals_supply_problem(self):
        details = self._make_details()
        details['psum'] = True
        vals = self.service._build_catalog_vals('99999', details)
        self.assertTrue(vals['supply_problem'])

    def test_build_catalog_vals_black_triangle(self):
        details = self._make_details()
        details['triangulo'] = True
        vals = self.service._build_catalog_vals('99999', details)
        self.assertTrue(vals['black_triangle'])

    def test_build_catalog_vals_no_principios_uses_pactivos(self):
        details = self._make_details()
        details['principiosActivos'] = []
        details['pactivos'] = 'PRINCIPIO FALLBACK'
        vals = self.service._build_catalog_vals('99999', details)
        self.assertEqual(vals['active_principles'], 'PRINCIPIO FALLBACK')

    def test_build_catalog_vals_empty_atcs(self):
        details = self._make_details()
        details['atcs'] = []
        vals = self.service._build_catalog_vals('99999', details)
        self.assertEqual(vals['atc_code'], '')
        self.assertEqual(vals['atc_description'], '')


# ---------------------------------------------------------------------------
# Tests live: ver tools/test_cima_api_live.py (requieren conexión a internet)
# El test runner de Odoo bloquea HTTP externo; ejecutar ese script por separado.
# ---------------------------------------------------------------------------
