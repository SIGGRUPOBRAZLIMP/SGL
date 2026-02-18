"""
Teste rápido do scraper BBMNET.
Roda: python testar_bbmnet.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

from bbmnet_scraper import BBMNETScraper, captar_editais_bbmnet

USERNAME = "07923334625"
PASSWORD = "Gbraz24@"

print("=" * 60)
print("TESTE SCRAPER BBMNET")
print("=" * 60)

scraper = BBMNETScraper(USERNAME, PASSWORD)

# 1. Autenticar
print("\n>>> ETAPA 1: Autenticação Keycloak")
print("-" * 40)
if scraper.autenticar():
    print("✅ Autenticado com sucesso!")
    print(f"   Token: {scraper.access_token[:60]}...")
else:
    print("❌ Falha na autenticação!")
    print("   Verifique usuário/senha.")
    sys.exit(1)

# 2. Buscar editais RJ (5 primeiros)
print("\n>>> ETAPA 2: Buscar editais RJ (Pregão, 5 primeiros)")
print("-" * 40)
resultado = scraper.buscar_editais(uf="RJ", modalidade_id=3, take=5)
count = resultado.get("count", 0)
editais = resultado.get("editais", [])
print(f"✅ Total no BBMNET (RJ, Pregão): {count}")
print(f"   Recebidos nesta página: {len(editais)}")

if editais:
    for i, ed in enumerate(editais):
        uid = ed.get("uniqueId", "?")[:15]
        num = ed.get("numeroEdital", "?")
        proc = ed.get("numeroProcesso", "?")
        print(f"   [{i+1}] Edital {num} | Processo {proc} | ID: {uid}...")

# 3. Detalhe do primeiro edital
if editais:
    uid = editais[0].get("uniqueId")
    print(f"\n>>> ETAPA 3: Detalhe do edital {uid[:20]}...")
    print("-" * 40)
    detalhe = scraper.buscar_detalhe_edital(uid)
    if detalhe:
        print(f"✅ Detalhe obtido!")
        print(f"   Órgão: {detalhe.get('orgaoPromotor', {}).get('razaoSocial', 'N/A')}")
        print(f"   Objeto: {(detalhe.get('objeto') or 'N/A')[:120]}...")
        print(f"   Modalidade: {detalhe.get('modalidade', {}).get('name', 'N/A')}")
        print(f"   Status: {detalhe.get('editalStatus', {}).get('name', 'N/A')}")
        print(f"   Publicado: {detalhe.get('publishAt', 'N/A')}")
        print(f"   Início Propostas: {detalhe.get('inicioRecebimentoPropostas', 'N/A')}")

        # Converter
        sgl = BBMNETScraper.converter_para_sgl(detalhe)
        print(f"\n   --- Convertido para formato SGL ---")
        print(f"   hash_unico: {sgl['hash_unico']}")
        print(f"   orgao: {sgl['orgao_razao_social']}")
        print(f"   uf: {sgl['uf']}")
        print(f"   plataforma: {sgl['plataforma_origem']}")
        print(f"   url: {sgl['url_original']}")
    else:
        print("❌ Não conseguiu obter detalhe")

# 4. Buscar MG também
print(f"\n>>> ETAPA 4: Buscar editais MG (5 primeiros)")
print("-" * 40)
resultado_mg = scraper.buscar_editais(uf="MG", modalidade_id=3, take=5)
count_mg = resultado_mg.get("count", 0)
editais_mg = resultado_mg.get("editais", [])
print(f"✅ Total no BBMNET (MG, Pregão): {count_mg}")
print(f"   Recebidos nesta página: {len(editais_mg)}")

if editais_mg:
    for i, ed in enumerate(editais_mg):
        num = ed.get("numeroEdital", "?")
        proc = ed.get("numeroProcesso", "?")
        print(f"   [{i+1}] Edital {num} | Processo {proc}")

print("\n" + "=" * 60)
print("TESTE CONCLUÍDO COM SUCESSO! ✅")
print("=" * 60)
print("\nO scraper BBMNET está funcional.")
print("Próximo passo: integrar ao captacao_service.py do SGL")
