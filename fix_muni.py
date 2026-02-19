path = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\api\routes.py'
content = open(path, 'r', encoding='utf-8').read()

old = "query = query.filter(db.or_(func.unaccent(Edital.municipio).ilike(func.unaccent(f'%{municipio}%')), func.unaccent(Edital.orgao_razao_social).ilike(func.unaccent(f'%{municipio}%'))))"

new = "query = query.filter(db.or_(func.unaccent(Edital.municipio).ilike(func.unaccent(f'%{municipio}%')), func.unaccent(Edital.orgao_razao_social).ilike(func.unaccent(f'%{municipio}%')), func.unaccent(Edital.objeto_resumo).ilike(func.unaccent(f'%{municipio}%'))))"

if old in content:
    content = content.replace(old, new)
    open(path, 'w', encoding='utf-8').write(content)
    print('OK - municipio busca tambem no objeto')
else:
    print('NAO ENCONTROU')
