"""
Fix: 
1. Filtro modalidade - buscar por palavras-chave parciais
2. Popular município extraindo do nome do órgão
3. Atualizar registros existentes sem município
"""

# ============================================================
# 1. Fix filtro modalidade no backend - usar OR com palavras
# ============================================================
path_routes = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\api\routes.py'
content = open(path_routes, 'r', encoding='utf-8').read()

old_mod = "if modalidade:\n        query = query.filter(Edital.modalidade_nome.ilike(f'%{modalidade}%'))"
new_mod = """if modalidade:
        # Buscar por palavras-chave (ex: "Pregão Eletrônico" match "Pregão - Eletrônico" e "Pregão (Setor público)")
        palavras = [p.strip() for p in modalidade.replace('(', ' ').replace(')', ' ').replace('-', ' ').split() if len(p.strip()) > 2]
        if palavras:
            filtros_mod = [Edital.modalidade_nome.ilike(f'%{p}%') for p in palavras]
            query = query.filter(db.and_(*filtros_mod))"""

if old_mod in content:
    content = content.replace(old_mod, new_mod)
    print('OK - Filtro modalidade agora busca por palavras-chave')
else:
    print('AVISO - bloco modalidade nao encontrado, tentando alternativo')
    # Tentar sem o if na frente
    old2 = "query = query.filter(Edital.modalidade_nome.ilike(f'%{modalidade}%'))"
    if old2 in content:
        new2 = """# Buscar por palavras-chave
        palavras = [p.strip() for p in modalidade.replace('(', ' ').replace(')', ' ').replace('-', ' ').split() if len(p.strip()) > 2]
        if palavras:
            filtros_mod = [Edital.modalidade_nome.ilike(f'%{p}%') for p in palavras]
            query = query.filter(db.and_(*filtros_mod))
        else:
            query = query.filter(Edital.modalidade_nome.ilike(f'%{modalidade}%'))"""
        content = content.replace(old2, new2)
        print('OK - Filtro modalidade corrigido (alternativo)')

open(path_routes, 'w', encoding='utf-8').write(content)

# ============================================================
# 2. Fix BBMNET converter - extrair município do nome do órgão
# ============================================================
path_bbmnet = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\services\bbmnet_scraper.py'
content = open(path_bbmnet, 'r', encoding='utf-8').read()

# Adicionar extração de município após a linha que define municipio
old_muni = '''        municipio = endereco.get("cidade", "") if isinstance(endereco, dict) else ""'''
new_muni = '''        municipio = endereco.get("cidade", "") if isinstance(endereco, dict) else ""
        
        # Extrair município do nome do órgão se não veio no endereço
        if not municipio:
            nome_orgao = orgao.get("razaoSocial") or orgao.get("nomeFantasia") or orgao.get("nome") or ""
            # Padrões: "Prefeitura Municipal De Piraí", "Câmara Municipal de Barra Mansa"
            import re
            match = re.search(r'(?:Municipal|Município|Municipio)\s+(?:De|de|DO|do|DA|da)\s+(.+?)(?:\s*[-/]|$)', nome_orgao)
            if match:
                municipio = match.group(1).strip()
            elif " de " in nome_orgao.lower():
                # "Fundo Municipal de Saúde de Pinheiral" -> "Pinheiral"
                parts = nome_orgao.split(" de ")
                if len(parts) >= 3:
                    municipio = parts[-1].strip().rstrip("/")'''

if old_muni in content:
    content = content.replace(old_muni, new_muni)
    open(path_bbmnet, 'w', encoding='utf-8').write(content)
    print('OK - BBMNET: extração de município do nome do órgão')
else:
    print('AVISO - bloco municipio BBMNET nao encontrado')

# ============================================================
# 3. Fix PNCP captacao_service - extrair município
# ============================================================
path_captacao = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\services\captacao_service.py'
content = open(path_captacao, 'r', encoding='utf-8').read()

# Verificar se já tem municipio no mapeamento
if "'municipio'" not in content and '"municipio"' not in content:
    # Procurar onde monta o dict do edital pra adicionar municipio
    print('AVISO - PNCP captacao_service nao tem campo municipio no mapeamento')
    # Vamos ver o que tem
    if 'orgao_razao_social' in content:
        print('  -> tem orgao_razao_social, pode extrair municipio dele')
else:
    print('PNCP captacao_service ja tem campo municipio')

# ============================================================
# 4. Script para atualizar municípios existentes no banco
# ============================================================
update_script = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\update_municipios.py'
with open(update_script, 'w', encoding='utf-8') as f:
    f.write('''"""Atualizar município dos editais existentes extraindo do nome do órgão"""
import re
import sys
sys.path.insert(0, '.')
from sgl.app import create_app
app = create_app()

def extrair_municipio(nome_orgao):
    if not nome_orgao:
        return None
    match = re.search(r'(?:Municipal|Município|Municipio)\\s+(?:De|de|DO|do|DA|da)\\s+(.+?)(?:\\s*[-/]|$)', nome_orgao)
    if match:
        return match.group(1).strip()
    if " de " in nome_orgao.lower():
        parts = nome_orgao.split(" de ")
        if len(parts) >= 3:
            return parts[-1].strip().rstrip("/")
    return None

with app.app_context():
    from sgl.models.database import db, Edital
    editais = Edital.query.filter(
        db.or_(Edital.municipio == None, Edital.municipio == '')
    ).all()
    print(f"Editais sem município: {len(editais)}")
    updated = 0
    for e in editais:
        muni = extrair_municipio(e.orgao_razao_social)
        if muni:
            e.municipio = muni
            updated += 1
    db.session.commit()
    print(f"Atualizados: {updated}")
''')
print(f'OK - Script update_municipios.py criado')

print('\n=== CORREÇÕES APLICADAS ===')
print('1. Filtro modalidade busca por palavras-chave')
print('2. BBMNET extrai município do nome do órgão')
print('3. Script update_municipios.py para corrigir existentes')
print('')
print('Próximo:')
print('  1. cd sgl-frontend && npm run build && cd ..')
print('  2. git add -A && git commit && git push')
print('  3. No Shell do Render: python update_municipios.py')
