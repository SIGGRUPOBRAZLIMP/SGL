"""
SGL - Descoberta de APIs do BBMNET e Licitar Digital
Roda localmente para encontrar os endpoints internos dessas plataformas.
"""
import requests
import json
import sys

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/html, */*',
    'Accept-Language': 'pt-BR,pt;q=0.9',
})

def testar_endpoint(nome, url, params=None, method='GET'):
    """Testa um endpoint e mostra o resultado."""
    try:
        if method == 'GET':
            r = session.get(url, params=params, timeout=15)
        else:
            r = session.post(url, json=params, timeout=15)
        
        content_type = r.headers.get('content-type', '')
        print(f"\n{'='*60}")
        print(f"[{nome}] {method} {url}")
        print(f"Status: {r.status_code} | Content-Type: {content_type}")
        
        if r.status_code == 200:
            if 'json' in content_type:
                data = r.json()
                texto = json.dumps(data, indent=2, ensure_ascii=False)
                print(f"JSON Response (primeiros 1500 chars):")
                print(texto[:1500])
                return True
            else:
                print(f"HTML/Text Response (primeiros 800 chars):")
                print(r.text[:800])
        else:
            print(f"Erro: {r.text[:300]}")
        return False
    except Exception as e:
        print(f"\n[{nome}] ERRO: {e}")
        return False


print("=" * 60)
print("DESCOBERTA DE APIs - BBMNET e LICITAR DIGITAL")
print("=" * 60)

# ============================================================
# BBMNET
# ============================================================
print("\n\n>>> TESTANDO BBMNET <<<")

bbmnet_endpoints = [
    # API possíveis do sistema
    ("BBMNET API editais", "https://sistema.bbmnet.com.br/api/editais", {'page': 1, 'uf': 'RJ'}),
    ("BBMNET API editais v2", "https://sistema.bbmnet.com.br/api/v1/editais", {'page': 1}),
    ("BBMNET API processos", "https://sistema.bbmnet.com.br/api/processos", {'page': 1}),
    ("BBMNET API licitacoes", "https://sistema.bbmnet.com.br/api/licitacoes", {'page': 1}),
    ("BBMNET API busca", "https://sistema.bbmnet.com.br/api/busca", {'termo': 'pregao'}),
    ("BBMNET visaoeditais API", "https://sistema.bbmnet.com.br/visaoeditais/api/editais", {'page': 1}),
    ("BBMNET visaoeditais busca", "https://sistema.bbmnet.com.br/visaoeditais/api/busca", {'uf': 'RJ'}),
    # Gateway patterns
    ("BBMNET gateway editais", "https://api.bbmnet.com.br/editais", {'page': 1}),
    ("BBMNET gateway processos", "https://api.bbmnet.com.br/processos", {'page': 1}),
    ("BBMNET gateway v1", "https://api.bbmnetlicitacoes.com.br/v1/editais", {'page': 1}),
    # Jornal do licitante
    ("BBMNET jornal API", "https://jornaldolicitante.com.br/api/editais", {'page': 1}),
    ("BBMNET jornal busca", "https://jornaldolicitante.com.br/api/busca", {'uf': 'RJ'}),
    ("BBMNET jornal processos", "https://jornaldolicitante.com.br/api/processos", {}),
    # WP REST API (site novo é WordPress)
    ("BBMNET WP API", "https://bbmnet.com.br/wp-json/wp/v2/posts", {'per_page': 5}),
    ("BBMNET WP editais", "https://bbmnet.com.br/wp-json/bbmnet/v1/editais", {}),
]

for nome, url, params in bbmnet_endpoints:
    testar_endpoint(nome, url, params)


# ============================================================
# LICITAR DIGITAL
# ============================================================
print("\n\n>>> TESTANDO LICITAR DIGITAL <<<")

licitar_endpoints = [
    # App principal
    ("Licitar API processos", "https://app.licitardigital.com.br/api/processos", {'page': 1}),
    ("Licitar API editais", "https://app.licitardigital.com.br/api/editais", {'page': 1}),
    ("Licitar API busca", "https://app.licitardigital.com.br/api/busca", {'uf': 'MG'}),
    ("Licitar API licitacoes", "https://app.licitardigital.com.br/api/licitacoes", {}),
    ("Licitar API pesquisa", "https://app.licitardigital.com.br/api/pesquisa", {'uf': 'MG'}),
    # App2
    ("Licitar App2 API processos", "https://app2.licitardigital.com.br/api/processos", {'page': 1}),
    ("Licitar App2 API editais", "https://app2.licitardigital.com.br/api/editais", {'page': 1}),
    ("Licitar App2 API busca", "https://app2.licitardigital.com.br/api/busca", {}),
    ("Licitar App2 API pesquisa", "https://app2.licitardigital.com.br/api/pesquisa", {}),
    # Backend direto
    ("Licitar backend", "https://api.licitardigital.com.br/processos", {'page': 1}),
    ("Licitar backend v1", "https://api.licitardigital.com.br/v1/processos", {}),
    # Pesquisa pública
    ("Licitar pesquisa publica", "https://app.licitardigital.com.br/pesquisa", {}),
    ("Licitar pesquisa app2", "https://app2.licitardigital.com.br/pesquisa", {}),
    # GraphQL
    ("Licitar GraphQL", "https://app.licitardigital.com.br/graphql", {'query': '{ processos { id } }'}),
    ("Licitar App2 GraphQL", "https://app2.licitardigital.com.br/graphql", {}),
]

for nome, url, params in licitar_endpoints:
    testar_endpoint(nome, url, params)

# ============================================================
# Tentar POST para APIs comuns
# ============================================================
print("\n\n>>> TESTANDO POSTs <<<")

post_tests = [
    ("BBMNET POST editais", "https://sistema.bbmnet.com.br/api/editais/buscar", {'uf': 'RJ', 'modalidade': 'Pregão'}),
    ("BBMNET POST visao", "https://sistema.bbmnet.com.br/visaoeditais/api/buscar", {'uf': 'RJ'}),
    ("Licitar POST processos", "https://app.licitardigital.com.br/api/processos/buscar", {'uf': 'MG'}),
    ("Licitar POST pesquisa", "https://app.licitardigital.com.br/api/pesquisa", {'estado': 'MG', 'tipo': 'pregao'}),
    ("Licitar App2 POST", "https://app2.licitardigital.com.br/api/processos/buscar", {'uf': 'MG'}),
]

for nome, url, params in post_tests:
    testar_endpoint(nome, url, params, method='POST')


print("\n\n" + "=" * 60)
print("DESCOBERTA CONCLUÍDA")
print("=" * 60)
print("\nCopie TODO o output acima e envie no chat do Claude.")
print("Com base nas respostas, vou construir os scrapers corretos.")
