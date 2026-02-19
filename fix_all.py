"""Fix BBMNET UF, add cloudscraper, fix Licitar Digital"""
import os

# ============================================================
# 1. Fix BBMNET - extrair UF do orgaoPromotor
# ============================================================
path_bbmnet = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\services\bbmnet_scraper.py'
lines = open(path_bbmnet, 'r', encoding='utf-8').readlines()

for i, line in enumerate(lines):
    if 'if not uf and isinstance(edital_bbmnet.get("uf"), str):' in line:
        # Inserir antes: checar orgao.get("uf")
        new_lines = [
            '        if not uf and isinstance(orgao.get("uf"), str):\n',
            '            uf = orgao["uf"]\n',
        ]
        lines = lines[:i] + new_lines + lines[i:]
        print('OK - BBMNET: UF extraido de orgaoPromotor.uf')
        break
else:
    print('AVISO - linha UF nao encontrada no bbmnet_scraper')

open(path_bbmnet, 'w', encoding='utf-8').writelines(lines)

# ============================================================
# 2. Add cloudscraper to requirements.txt
# ============================================================
path_req = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\requirements.txt'
content = open(path_req, 'r', encoding='utf-8').read()
if 'cloudscraper' not in content:
    content = content.rstrip() + '\ncloudscraper>=1.2.71\n'
    open(path_req, 'w', encoding='utf-8').write(content)
    print('OK - cloudscraper adicionado ao requirements.txt')
else:
    print('cloudscraper ja esta no requirements.txt')

# ============================================================
# 3. Fix Licitar Digital scraper - usar cloudscraper
# ============================================================
path_licitar = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\services\licitardigital_scraper.py'
content = open(path_licitar, 'r', encoding='utf-8').read()

# Substituir import requests por cloudscraper
if 'import cloudscraper' not in content:
    # Adicionar import no topo
    old_import = 'import requests'
    new_import = 'import requests\ntry:\n    import cloudscraper\n    HAS_CLOUDSCRAPER = True\nexcept ImportError:\n    HAS_CLOUDSCRAPER = False'
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('OK - Licitar: import cloudscraper adicionado')

    # Substituir self.session = requests.Session() por cloudscraper
    old_session = 'self.session = requests.Session()'
    new_session = 'self.session = cloudscraper.create_scraper() if HAS_CLOUDSCRAPER else requests.Session()'
    if old_session in content:
        content = content.replace(old_session, new_session)
        print('OK - Licitar: session usa cloudscraper')
    else:
        print('AVISO - nao encontrei self.session = requests.Session()')

    open(path_licitar, 'w', encoding='utf-8').write(content)
else:
    print('cloudscraper ja importado no licitardigital_scraper')

print('\n=== TODAS AS CORRECOES APLICADAS ===')
print('Proximo: git add -A && git commit && git push')
