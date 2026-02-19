"""Testar busca BBMNET e PNCP para editais faltando"""
import sys
sys.path.insert(0, '.')

from sgl.services.bbmnet_scraper import BBMNETScraper

print("=== BBMNET - Testando busca ===")
scraper = BBMNETScraper("07923334625", "Gbraz24@")

if not scraper.autenticar():
    print("FALHA na autenticação BBMNET")
    sys.exit(1)

print("Autenticado OK\n")

# Buscar RJ - procurar Pirai
print("--- RJ (buscando Pirai PE13) ---")
result = scraper.buscar_editais(uf="RJ", modalidade_id=3, take=50, skip=0)
editais = result.get("result", result.get("data", []))
total = result.get("totalRegistros", result.get("total", len(editais)))
print(f"Total RJ: {total} editais, retornados: {len(editais)}")

for e in editais:
    orgao = e.get("orgao", {})
    razao = orgao.get("razaoSocial", "") if isinstance(orgao, dict) else str(orgao)
    objeto = str(e.get("objeto", ""))[:100]
    cidade = ""
    end = e.get("endereco", {})
    if isinstance(end, dict):
        cidade = end.get("municipio", "")
    
    # Procurar Pirai
    if "pirai" in razao.lower() or "pirai" in objeto.lower() or "pirai" in cidade.lower() or "piraí" in razao.lower() or "piraí" in cidade.lower():
        print(f"  >>> PIRAI ENCONTRADO: {razao} | {objeto}")
    
print()

# Buscar SP - procurar Aruja
print("--- SP (buscando Aruja PE04 e Mogi PE58) ---")
result = scraper.buscar_editais(uf="SP", modalidade_id=3, take=50, skip=0)
editais = result.get("result", result.get("data", []))
total = result.get("totalRegistros", result.get("total", len(editais)))
print(f"Total SP: {total} editais, retornados: {len(editais)}")

for e in editais:
    orgao = e.get("orgao", {})
    razao = orgao.get("razaoSocial", "") if isinstance(orgao, dict) else str(orgao)
    objeto = str(e.get("objeto", ""))[:100]
    cidade = ""
    end = e.get("endereco", {})
    if isinstance(end, dict):
        cidade = end.get("municipio", "")
    
    # Procurar Aruja ou Mogi
    texto = (razao + objeto + cidade).lower()
    if "aruj" in texto or "mogi" in texto:
        print(f"  >>> ENCONTRADO: {razao} | {cidade} | {objeto}")

print()

# Listar os 10 primeiros de cada UF pra ver o que vem
print("--- Amostra RJ (10 primeiros) ---")
result = scraper.buscar_editais(uf="RJ", modalidade_id=3, take=10, skip=0)
editais = result.get("result", result.get("data", []))
for i, e in enumerate(editais):
    orgao = e.get("orgao", {})
    razao = orgao.get("razaoSocial", "") if isinstance(orgao, dict) else str(orgao)
    obj = str(e.get("objeto", ""))[:60]
    uid = e.get("uniqueId", "?")
    print(f"  {i+1}. [{uid}] {razao[:40]} | {obj}")

print()
print("--- Amostra SP (10 primeiros) ---")
result = scraper.buscar_editais(uf="SP", modalidade_id=3, take=10, skip=0)
editais = result.get("result", result.get("data", []))
for i, e in enumerate(editais):
    orgao = e.get("orgao", {})
    razao = orgao.get("razaoSocial", "") if isinstance(orgao, dict) else str(orgao)
    obj = str(e.get("objeto", ""))[:60]
    uid = e.get("uniqueId", "?")
    print(f"  {i+1}. [{uid}] {razao[:40]} | {obj}")
