"""
Script de pruebas live contra la API real de CIMA (AEMPS).

Ejecutar FUERA de Odoo (el test runner de Odoo bloquea HTTP externo):
    python3 custom-addons/cs_cima/tools/test_cima_api_live.py

Requiere conexión a internet. No necesita credenciales ni Odoo instalado.
"""
import sys
import requests

BASE = 'https://cima.aemps.es/cima/rest'
PASS = '\033[92m✓\033[0m'
FAIL = '\033[91m✗\033[0m'

errors = []


def check(condition, msg):
    if condition:
        print(f'  {PASS} {msg}')
    else:
        print(f'  {FAIL} {msg}')
        errors.append(msg)


def section(title):
    print(f'\n\033[1m{title}\033[0m')


# ---------------------------------------------------------------------------
# Test 1: GET /medicamentos — parámetro comerc=1
# ---------------------------------------------------------------------------

section('TEST 1: GET /medicamentos — parámetro comerc=1 (no comercc)')

r_comerc = requests.get(f'{BASE}/medicamentos', params={'nombre': 'omeprazol', 'comerc': 1}, timeout=8)
r_comercc = requests.get(f'{BASE}/medicamentos', params={'nombre': 'omeprazol', 'comercc': 1}, timeout=8)
r_all = requests.get(f'{BASE}/medicamentos', params={'nombre': 'omeprazol'}, timeout=8)

total_comerc = r_comerc.json().get('totalFilas', 0)
total_comercc = r_comercc.json().get('totalFilas', 0)
total_all = r_all.json().get('totalFilas', 0)

check(r_comerc.status_code == 200, f'Status 200 con comerc=1')
check(total_comerc > 0, f'comerc=1 devuelve resultados ({total_comerc})')
check(total_comerc < total_comercc, f'comerc=1 ({total_comerc}) filtra más que comercc=1 ({total_comercc}) — comercc es incorrecto')
check(total_comerc <= total_all, f'comerc=1 ({total_comerc}) ≤ sin filtro ({total_all})')

# Verificar que todos los resultados tienen comerc=True
results = r_comerc.json().get('resultados', [])
non_commercial = [r for r in results if not r.get('comerc')]
check(len(non_commercial) == 0, f'Todos los resultados con comerc=1 tienen comerc=True ({len(results)} medicamentos)')

# ---------------------------------------------------------------------------
# Test 2: GET /medicamento — estructura de respuesta
# ---------------------------------------------------------------------------

section('TEST 2: GET /medicamento?nregistro=82921 — estructura completa')

r = requests.get(f'{BASE}/medicamento', params={'nregistro': '82921'}, timeout=8)
d = r.json()

check(r.status_code == 200, 'Status 200')
check(d.get('nregistro') == '82921', f'nregistro correcto: {d.get("nregistro")}')
check('nombre' in d, f'Tiene campo nombre: {d.get("nombre")}')
check('pactivos' in d, f'Tiene pactivos: {d.get("pactivos")}')
check('labtitular' in d, f'Tiene labtitular: {d.get("labtitular")}')
check('estado' in d, f'Tiene estado')
check('aut' in d.get('estado', {}), f'estado.aut presente: {d.get("estado", {}).get("aut")}')
check('rev' not in d.get('estado', {}), f'estado.rev ausente en medicamento activo ✓')
check('atcs' in d and len(d['atcs']) > 0, f'Tiene ATCs: {len(d.get("atcs", []))} entradas')
check('principiosActivos' in d, f'Tiene principiosActivos')
check('viasAdministracion' in d, f'Tiene viasAdministracion')
check('formaFarmaceutica' in d, f'Tiene formaFarmaceutica')
check('cpresc' in d, f'Tiene cpresc: {d.get("cpresc")}')
check('receta' in d, f'Tiene receta: {d.get("receta")}')
check('conduc' in d, f'Tiene conduc: {d.get("conduc")}')
check('triangulo' in d, f'Tiene triangulo: {d.get("triangulo")}')
check('psum' in d, f'Tiene psum: {d.get("psum")}')

# ---------------------------------------------------------------------------
# Test 3: Estado de medicamento revocado
# ---------------------------------------------------------------------------

section('TEST 3: Estado.rev en medicamento revocado (nregistro=86114)')

r2 = requests.get(f'{BASE}/medicamento', params={'nregistro': '86114'}, timeout=8)
d2 = r2.json()
estado2 = d2.get('estado', {})

check(r2.status_code == 200, 'Status 200')
check('rev' in estado2, f'estado.rev presente: {estado2.get("rev")}')
check(isinstance(estado2.get('rev'), (int, float)), f'estado.rev es timestamp numérico: {estado2.get("rev")}')
check(estado2.get('rev') is not None and estado2.get('rev') > 0, f'estado.rev es positivo (timestamp válido)')
check(not d2.get('comerc', True), f'Medicamento revocado tiene comerc=False')

# ---------------------------------------------------------------------------
# Test 4: _map_route con datos reales
# ---------------------------------------------------------------------------

section('TEST 4: _map_route — mapeo de viasAdministracion')

vias_tests = {
    '82921': ('VÍA ORAL', 'oral'),
}

for nregistro, (expected_via, expected_route) in vias_tests.items():
    r3 = requests.get(f'{BASE}/medicamento', params={'nregistro': nregistro}, timeout=8)
    d3 = r3.json()
    vias = d3.get('viasAdministracion', [])
    nombre = vias[0].get('nombre', '') if vias else ''
    check(nombre == expected_via, f'nregistro {nregistro}: viasAdministracion[0].nombre = {nombre!r}')
    # Simular _map_route
    ROUTE_MAP = {
        'oral': 'oral', 'sublingual': 'sublingual', 'rectal': 'rectal',
        'intravenosa': 'intravenosa', 'intramuscular': 'intramuscular',
        'subcutánea': 'subcutanea', 'subcutanea': 'subcutanea',
        'tópic': 'topica', 'cutánea': 'topica', 'cutanea': 'topica',
        'inhalat': 'inhalada', 'transdérm': 'transdermico', 'transderm': 'transdermico',
    }
    nombre_lower = nombre.lower()
    mapped = next((v for k, v in ROUTE_MAP.items() if k in nombre_lower), 'oral')
    check(mapped == expected_route, f'_map_route({nombre!r}) = {mapped!r} (esperado: {expected_route!r})')

# ---------------------------------------------------------------------------
# Test 5: ATC más específico
# ---------------------------------------------------------------------------

section('TEST 5: ATCs ordenados de genérico a específico')

atcs = d.get('atcs', [])
niveles = [a['nivel'] for a in atcs]
check(niveles == sorted(niveles), f'ATCs ordenados por nivel ascendente: {niveles}')
check(atcs[-1]['nivel'] == max(niveles), f'Último ATC es el más específico: {atcs[-1]["codigo"]} nivel {atcs[-1]["nivel"]}')
check(atcs[-1]['codigo'] == 'A02BC05', f'ATC específico correcto: {atcs[-1]["codigo"]}')

# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------

print()
if errors:
    print(f'\033[91m{len(errors)} test(s) fallaron:\033[0m')
    for e in errors:
        print(f'  - {e}')
    sys.exit(1)
else:
    total = 30  # count aproximado
    print(f'\033[92mTodos los tests live pasaron correctamente.\033[0m')
    sys.exit(0)
