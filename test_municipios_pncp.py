"""Test PNCP coverage for BR Conectado municipalities"""
import requests

print('=== Busca municipios no PNCP ===')
cnpjs = {
    'Pref Sao Jose dos Campos': '46643466000106',
    'Pref Cacapava': '45176071000108',
    'Pref Guaratingueta': '58550925000105',
    'Pref Lorena': '67513926000163'
}

# Modalidades: 1=Pregao, 2=Concorrencia, 4=Dispensa, 6=Inexigibilidade, 8=Pregao Eletronico
modalidades = [1, 2, 4, 6, 8]

for nome, cnpj in cnpjs.items():
    total_geral = 0
    plataformas = set()
    for mod in modalidades:
        try:
            r = requests.get(
                'https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao',
                params={
                    'dataInicial': '20250101',
                    'dataFinal': '20260218',
                    'codigoModalidadeContratacao': mod,
                    'cnpj': cnpj,
                    'pagina': 1,
                    'tamanhoPagina': 10
                },
                timeout=30
            )
            if r.ok:
                data = r.json()
                total = data.get('totalRegistros', 0)
                total_geral += total
                for item in data.get('data', []):
                    link = item.get('linkSistemaOrigem', '')
                    if link:
                        # Extract platform domain
                        domain = link.split('/')[2] if len(link.split('/')) > 2 else link
                        plataformas.add(domain)
        except:
            pass

    print(f'{nome} ({cnpj}):')
    print(f'  Total editais 2025-2026: {total_geral}')
    if plataformas:
        print(f'  Plataformas detectadas:')
        for p in sorted(plataformas):
            print(f'    - {p}')
    else:
        print(f'  Nenhuma plataforma detectada (pode nao ter publicado)')
    print()
