"""Fix: usar unaccent no PostgreSQL para busca sem acento"""
path = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\api\routes.py'
content = open(path, 'r', encoding='utf-8').read()

# Adicionar import do func do sqlalchemy se não tem
if 'from sqlalchemy import func' not in content and 'sqlalchemy' not in content.split('def listar_editais')[0][-200:]:
    # Adicionar no inicio da funcao
    old_import = 'from datetime import datetime'
    new_import = 'from datetime import datetime\n    from sqlalchemy import func'
    content = content.replace(old_import, new_import, 1)
    print('OK - import func adicionado')

# Substituir todos os ilike por unaccent+ilike
# Padrão: Campo.ilike(f'%{var}%') -> db.func.unaccent(Campo).ilike(db.func.unaccent(f'%{var}%'))

replacements = [
    # Busca geral
    ("Edital.objeto_resumo.ilike(f'%{busca}%')", "func.unaccent(Edital.objeto_resumo).ilike(func.unaccent(f'%{busca}%'))"),
    ("Edital.orgao_razao_social.ilike(f'%{busca}%')", "func.unaccent(Edital.orgao_razao_social).ilike(func.unaccent(f'%{busca}%'))"),
    ("Edital.numero_pregao.ilike(f'%{busca}%')", "Edital.numero_pregao.ilike(f'%{busca}%')"),  # numero nao precisa unaccent
    ("Edital.municipio.ilike(f'%{busca}%')", "func.unaccent(Edital.municipio).ilike(func.unaccent(f'%{busca}%'))"),
    
    # Modalidade
    ("Edital.modalidade_nome.ilike(f'%{p}%')", "func.unaccent(Edital.modalidade_nome).ilike(func.unaccent(f'%{p}%'))"),
    
    # Municipio
    ("Edital.municipio.ilike(f'%{municipio}%')", "func.unaccent(Edital.municipio).ilike(func.unaccent(f'%{municipio}%'))"),
    ("Edital.orgao_razao_social.ilike(f'%{municipio}%')", "func.unaccent(Edital.orgao_razao_social).ilike(func.unaccent(f'%{municipio}%'))"),
]

count = 0
for old, new in replacements:
    if old in content and old != new:
        content = content.replace(old, new)
        count += 1

print(f'OK - {count} filtros atualizados com unaccent')

open(path, 'w', encoding='utf-8').write(content)
print('DONE')
