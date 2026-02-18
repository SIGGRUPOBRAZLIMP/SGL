import requests

BASE = 'https://pncp.gov.br/api/consulta/v1'

for uf in ['RJ', 'MG', 'SP']:
    r = requests.get(
        f'{BASE}/contratacoes/publicacao',
        params={
            'dataInicial': '20260201',
            'dataFinal': '20260218',
            'codigoModalidadeContratacao': 8,
            'uf': uf,
            'pagina': 1,
            'tamanhoPagina': 20,
        },
        timeout=30,
    )
    data = r.json()
    total = data.get('totalRegistros', '?')
    print(f'\n=== {uf} - Total pregoes eletronicos fev/2026: {total} ===')
    for x in data.get('data', []):
        orgao = x.get('unidadeOrgao', {})
        nome = orgao.get('nomeUnidade', '')
        mun = orgao.get('municipioNome', '') or x.get('municipioNome', '')
        obj = (x.get('objetoCompra') or '')[:70]
        link = x.get('linkSistemaOrigem', '')
        plat = ''
        if link:
            parts = link.split('/')
            plat = parts[2] if len(parts) > 2 else link
        print(f'  [{mun}] {nome}')
        print(f'    {obj}')
        if plat:
            print(f'    Plataforma: {plat}')
