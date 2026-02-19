"""Fix filtros modalidade e municipio"""
path = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\api\routes.py'
content = open(path, 'r', encoding='utf-8').read()

# Fix 1: mudar AND para OR no filtro modalidade
old = 'query = query.filter(db.and_(*filtros_mod))'
new = 'query = query.filter(db.or_(*filtros_mod))'
if old in content:
    content = content.replace(old, new)
    print('OK - modalidade: AND -> OR')
else:
    print('AVISO - and_ nao encontrado')

# Fix 2: municipio buscar tambem no orgao_razao_social
old2 = "Edital.municipio.ilike(f'%{municipio}%')"
new2 = "db.or_(Edital.municipio.ilike(f'%{municipio}%'), Edital.orgao_razao_social.ilike(f'%{municipio}%'))"
if old2 in content:
    content = content.replace(old2, new2)
    print('OK - municipio: busca tambem no orgao')
else:
    print('AVISO - municipio nao encontrado')

open(path, 'w', encoding='utf-8').write(content)
print('DONE')
