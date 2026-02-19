"""Descobrir parametros de busca da API BBMNET"""
import sys
sys.path.insert(0, '.')
from sgl.services.bbmnet_scraper import BBMNETScraper

scraper = BBMNETScraper('07923334625', 'Gbraz24@')
scraper.autenticar()

BASE = 'https://bbmnet-cadastro-editais-backend-z7knklmt7a-rj.a.run.app'

# 1. Testar parametros extras
params_test = [
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'Search': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'Busca': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'Texto': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'Palavra': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'Municipio': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'Cidade': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'OrgaoPromotor': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'Objeto': 'papelaria'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'FiltroTexto': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'q': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'query': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'filter': 'aruja'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'TextoBusca': 'aruja'},
]

print("=== Testando parametros de busca ===")
for p in params_test:
    extra_key = [k for k in p.keys() if k not in ['Uf','ModalidadeId','Take','Skip']][0]
    try:
        resp = scraper.session.get(
            f'{BASE}/api/Editais/Participantes',
            params=p, timeout=15
        )
        if resp.status_code == 200 and resp.text:
            data = resp.json()
            count = data.get('count', 0)
            n = len(data.get('editais', []))
            # Se retornou menos que sem filtro, o parametro funcionou
            print(f"  {extra_key}=aruja -> {resp.status_code} | count={count} editais={n}")
        else:
            print(f"  {extra_key} -> {resp.status_code} | body={resp.text[:80]}")
    except Exception as e:
        print(f"  {extra_key} -> ERRO: {e}")

# 2. Testar outros endpoints
print("\n=== Testando outros endpoints ===")
endpoints = [
    '/api/Editais',
    '/api/Editais/Busca',
    '/api/Editais/Search',
    '/api/Editais/Pesquisar',
    '/api/Editais/Filtrar',
    '/api/Edital',
    '/api/Edital/Buscar',
    '/swagger',
    '/swagger/index.html',
    '/api-docs',
]
for ep in endpoints:
    try:
        resp = scraper.session.get(f'{BASE}{ep}', timeout=10)
        print(f"  {ep} -> {resp.status_code} | {resp.text[:100]}")
    except Exception as e:
        print(f"  {ep} -> ERRO: {e}")

# 3. Ver se tem Segmento como parametro (segmento = categoria de produto)
print("\n=== Testando filtro por Segmento ===")
seg_params = [
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'SegmentoId': 1},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'Segmento': 'limpeza'},
    {'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'CategoriaId': 1},
]
for p in seg_params:
    extra_key = [k for k in p.keys() if k not in ['Uf','ModalidadeId','Take','Skip']][0]
    try:
        resp = scraper.session.get(f'{BASE}/api/Editais/Participantes', params=p, timeout=15)
        if resp.status_code == 200 and resp.text:
            data = resp.json()
            count = data.get('count', 0)
            print(f"  {extra_key}={p[extra_key]} -> count={count}")
        else:
            print(f"  {extra_key} -> {resp.status_code}")
    except Exception as e:
        print(f"  {extra_key} -> ERRO: {e}")

# 4. Testar OrderBy e paginacao maior
print("\n=== Testando ordenacao e paginacao ===")
for order in ['DataPublicacao', 'DataRealizacao', 'publishAt', 'createdAt']:
    try:
        resp = scraper.session.get(
            f'{BASE}/api/Editais/Participantes',
            params={'Uf': 'SP', 'ModalidadeId': 3, 'Take': 3, 'Skip': 0, 'OrderBy': order},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            first = data.get('editais', [{}])[0] if data.get('editais') else {}
            pub = first.get('publishAt', first.get('createdAt', '?'))
            print(f"  OrderBy={order} -> count={data.get('count',0)} first_date={pub}")
    except Exception as e:
        print(f"  OrderBy={order} -> ERRO: {e}")
