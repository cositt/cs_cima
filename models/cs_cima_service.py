import logging
import requests
from odoo import models, api, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CIMA_BASE_URL = 'https://cima.aemps.es/cima/rest'
CIMA_PUBLIC_URL = 'https://cima.aemps.es/cima/publico/detalle.html'

# Mapeo de viasAdministracion[].nombre (uppercase desde CIMA) a selection values
ROUTE_MAP = {
    'oral': 'oral',
    'sublingual': 'sublingual',
    'rectal': 'rectal',
    'intravenosa': 'intravenosa',
    'intramuscular': 'intramuscular',
    'subcutánea': 'subcutanea',
    'subcutanea': 'subcutanea',
    'tópic': 'topica',
    'cutánea': 'topica',
    'cutanea': 'topica',
    'inhalat': 'inhalada',
    'transdérm': 'transdermico',
    'transderm': 'transdermico',
}


class CimaApiService(models.AbstractModel):
    _name = 'cs.cima.api.service'
    _description = 'Servicio API CIMA (AEMPS) — gratuito, sin API key'

    def _is_api_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'cs_cima.cima_api_enabled', 'True'
        ) == 'True'

    def _map_route(self, vias: list) -> str:
        """Mapea viasAdministracion[0].nombre al selection de route."""
        if not vias:
            return 'oral'
        nombre = (vias[0].get('nombre') or '').lower()
        for key, val in ROUTE_MAP.items():
            if key in nombre:
                return val
        return 'oral'

    def _map_status(self, estado: dict) -> str:
        """
        estado.rev / estado.susp son Unix timestamps (int) cuando el medicamento
        ha sido revocado o suspendido. Ausentes o None indica autorizado.
        """
        if not estado:
            return 'available'
        if estado.get('rev') or estado.get('susp'):
            return 'deleted'
        return 'available'

    def _build_catalog_vals(self, nregistro: str, details: dict) -> dict:
        """Construye el dict de valores para cs.drug.catalog desde la respuesta CIMA."""
        atcs = details.get('atcs') or []
        principios = details.get('principiosActivos') or []
        forma = details.get('formaFarmaceutica') or {}

        active_principles = ', '.join(
            p.get('nombre', '') for p in principios
        ) or details.get('pactivos', '')

        # Usar el ATC más específico (último elemento = nivel más alto)
        atc_entry = atcs[-1] if atcs else {}

        return {
            'name': details.get('nombre', f'MED-{nregistro}'),
            'active_principles': active_principles,
            'galenical_form': forma.get('nombre', ''),
            'route': self._map_route(details.get('viasAdministracion') or []),
            'atc_code': atc_entry.get('codigo', ''),
            'atc_description': atc_entry.get('nombre', ''),
            'laboratory': details.get('labtitular', ''),
            'market_status': self._map_status(details.get('estado') or {}),
            'cima_nregistro': str(nregistro),
            'last_sync_date': fields.Datetime.now(),
            'prescription_conditions': details.get('cpresc', ''),
            'requires_prescription': bool(details.get('receta')),
            'affects_driving': bool(details.get('conduc')),
            'black_triangle': bool(details.get('triangulo')),
            'supply_problem': bool(details.get('psum')),
        }

    def search_drugs(self, query: str) -> list:
        """
        Busca medicamentos en CIMA por nombre.
        Param correcto: comerc=1 (solo comercializados).
        Devuelve lista de objetos Lista de medicamentos de la API.
        """
        if not self._is_api_enabled() or not query or len(query) < 2:
            return []
        try:
            resp = requests.get(
                f'{CIMA_BASE_URL}/medicamentos',
                params={'nombre': query, 'comerc': 1},
                timeout=5,
            )
            resp.raise_for_status()
            return resp.json().get('resultados', [])
        except requests.exceptions.Timeout:
            _logger.warning('CIMA API timeout buscando: %s', query)
            return []
        except requests.exceptions.RequestException as e:
            _logger.error('CIMA API search error: %s', e)
            return []

    def get_drug_details(self, nregistro: str) -> dict:
        """Devuelve el objeto Medicamento completo desde GET /medicamento?nregistro=."""
        try:
            resp = requests.get(
                f'{CIMA_BASE_URL}/medicamento',
                params={'nregistro': nregistro},
                timeout=5,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            _logger.error('CIMA get_drug_details(%s) error: %s', nregistro, e)
            return {}

    @api.model
    def get_or_create_catalog(self, nregistro: str, details: dict = None) -> int:
        """
        Devuelve el id de cs.drug.catalog para el nregistro dado.
        Si no existe en el catálogo local, lo importa desde CIMA.
        Acepta details pre-fetched para evitar una llamada extra a la API.
        """
        existing = self.env['cs.drug.catalog'].search(
            [('cima_nregistro', '=', str(nregistro))], limit=1
        )
        if existing:
            return existing.id

        if details is None:
            details = self.get_drug_details(nregistro)
        if not details:
            raise UserError(
                _('No se encontró el medicamento en CIMA con nregistro %s') % nregistro
            )

        vals = self._build_catalog_vals(nregistro, details)
        drug = self.env['cs.drug.catalog'].create(vals)
        return drug.id
