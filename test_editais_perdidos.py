"""Teste direto na API PNCP para os 3 editais nao capturados"""
import requests

BASE = 'https://pncp.gov.br/api/consulta/v1'

testes = [
    {'uf': 'RJ', 'dataInicial': '20260215', 'dataFinal': '20260218', 'label': 'RJ ultimos dias'},
    {'uf': 'MG', 'dataInicial': '20260215', 'dataFinal': '20260218', 'label': 'MG ultimos dias'},
    {'uf': 'SP', 'dataInicial': '20260218', 'dataFinal': '20260218', 'label': 'SP hoje (controle)'},
    {'uf': None, 'dataInicial': '20260218', 'dataFinal': '20260218', 'label': 'TODAS UFs hoje'},
]

for t in testes:
    print(f"\n=== {t['label']} ===")
    params = {
        'dataInicial': t['dataInicial'],
        'dataFinal': t['dataFinal'],
        'codigoModalidadeContratacao': 8,
        'pagina': 1,
        'tamanhoPagina': 5,
    }
    if t['uf']:
        params['uf'] = t['uf']
    try:
        r = requests.get(f'{BASE}/contratacoes/publicacao', params=params, timeout=30)
        print(f"  Status: {r.status_code}")
        if r.ok:
            data = r.json()
            total = data.get('totalRegistros', 0) if isinstance(data, dict) else len(data)
            print(f"  Total: {total}")
            items = data.get('data', data) if isinstance(data, dict) else data
            for item in (items or [])[:3]:
                mun = item.get('municipioNome', 'N/A')
                obj = (item.get('objetoCompra') or '')[:80]
                print(f"  - [{mun}] {obj}")
        else:
            print(f"  Resposta: {r.text[:200]}")
    except Exception as e:
        print(f"  ERRO: {e}")
