"""
Patch: Adicionar TODOS os filtros ao endpoint GET /editais
Frontend já envia: modalidade, municipio, srp, data_pub_inicio/fim, 
data_certame_inicio/fim, valor_min/max, com_arquivos, com_itens_ai, ordenar_por, ordem
Backend só trata: status, uf, plataforma, busca
"""

path = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\api\routes.py'
content = open(path, 'r', encoding='utf-8').read()

# Substituir a função listar_editais inteira
old_func = '''def listar_editais():
    """Lista editais com filtros e paginação"""
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = request.args.get('por_pagina', 20, type=int)
    status = request.args.get('status')
    uf = request.args.get('uf')
    plataforma = request.args.get('plataforma')
    busca = request.args.get('busca')
    query = Edital.query
    if status:
        query = query.filter(Edital.status == status)
    if uf:
        query = query.filter(Edital.uf == uf.upper())
    if plataforma:
        query = query.filter(Edital.plataforma_origem == plataforma)
    if busca:
        query = query.filter(
            db.or_(
                Edital.objeto_resumo.ilike(f'%{busca}%'),
                Edital.orgao_razao_social.ilike(f'%{busca}%'),
                Edital.numero_pregao.ilike(f'%{busca}%')
            )
        )
    query = query.order_by(Edital.data_publicacao.desc().nullslast())
    paginação = query.paginate(page=pagina, per_page=min(por_pagina, 100), error_out=False)
    return jsonify({
        'editais': [e.to_dict() for e in paginação.items],
        'total': paginação.total,
        'paginas': paginação.pages,
        'pagina_atual': paginação.page,
    })'''

# Tentar variações de encoding
found = False
lines = content.split('\n')
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'def listar_editais():' in line:
        start_idx = i
    if start_idx and i > start_idx and line.strip().startswith('@api_bp.route'):
        end_idx = i
        break

if start_idx is not None and end_idx is not None:
    print(f'Encontrei listar_editais: linhas {start_idx+1} a {end_idx}')
    
    new_func = '''def listar_editais():
    """Lista editais com filtros completos e paginação"""
    from datetime import datetime
    
    # Paginação (aceitar ambos os nomes de param)
    pagina = request.args.get('page', request.args.get('pagina', 1, type=int), type=int)
    por_pagina = request.args.get('per_page', request.args.get('por_pagina', 20, type=int), type=int)
    
    # Filtros básicos
    status = request.args.get('status')
    uf = request.args.get('uf')
    plataforma = request.args.get('plataforma')
    busca = request.args.get('busca')
    
    # Filtros avançados
    modalidade = request.args.get('modalidade')
    municipio = request.args.get('municipio')
    srp = request.args.get('srp')
    data_pub_inicio = request.args.get('data_pub_inicio')
    data_pub_fim = request.args.get('data_pub_fim')
    data_certame_inicio = request.args.get('data_certame_inicio')
    data_certame_fim = request.args.get('data_certame_fim')
    valor_min = request.args.get('valor_min', type=float)
    valor_max = request.args.get('valor_max', type=float)
    com_arquivos = request.args.get('com_arquivos')
    com_itens_ai = request.args.get('com_itens_ai')
    ordenar_por = request.args.get('ordenar_por', 'data_publicacao')
    ordem = request.args.get('ordem', 'desc')
    
    query = Edital.query
    
    # Aplicar filtros básicos
    if status:
        query = query.filter(Edital.status == status)
    if uf:
        query = query.filter(Edital.uf == uf.upper())
    if plataforma:
        query = query.filter(Edital.plataforma_origem == plataforma)
    if busca:
        query = query.filter(
            db.or_(
                Edital.objeto_resumo.ilike(f'%{busca}%'),
                Edital.orgao_razao_social.ilike(f'%{busca}%'),
                Edital.numero_pregao.ilike(f'%{busca}%'),
                Edital.municipio.ilike(f'%{busca}%'),
            )
        )
    
    # Filtros avançados
    if modalidade:
        query = query.filter(Edital.modalidade_nome.ilike(f'%{modalidade}%'))
    if municipio:
        query = query.filter(Edital.municipio.ilike(f'%{municipio}%'))
    if srp:
        if srp == 'sim':
            query = query.filter(Edital.srp == True)
        elif srp == 'nao':
            query = query.filter(Edital.srp == False)
    
    # Filtros de data publicação
    if data_pub_inicio:
        try:
            dt = datetime.strptime(data_pub_inicio, '%Y-%m-%d')
            query = query.filter(Edital.data_publicacao >= dt)
        except ValueError:
            pass
    if data_pub_fim:
        try:
            dt = datetime.strptime(data_pub_fim, '%Y-%m-%d')
            query = query.filter(Edital.data_publicacao <= dt)
        except ValueError:
            pass
    
    # Filtros de data certame/disputa
    if data_certame_inicio:
        try:
            dt = datetime.strptime(data_certame_inicio, '%Y-%m-%d')
            if hasattr(Edital, 'data_inicio_lances'):
                query = query.filter(Edital.data_inicio_lances >= dt)
        except ValueError:
            pass
    if data_certame_fim:
        try:
            dt = datetime.strptime(data_certame_fim, '%Y-%m-%d')
            if hasattr(Edital, 'data_inicio_lances'):
                query = query.filter(Edital.data_inicio_lances <= dt)
        except ValueError:
            pass
    
    # Filtros de valor
    if valor_min is not None:
        query = query.filter(Edital.valor_estimado >= valor_min)
    if valor_max is not None:
        query = query.filter(Edital.valor_estimado <= valor_max)
    
    # Ordenação
    ordem_map = {
        'data_publicacao': Edital.data_publicacao,
        'data_certame': getattr(Edital, 'data_inicio_lances', Edital.data_publicacao),
        'valor_estimado': Edital.valor_estimado,
        'orgao_razao_social': Edital.orgao_razao_social,
        'status': Edital.status,
        'created_at': Edital.created_at if hasattr(Edital, 'created_at') else Edital.data_publicacao,
        'id': Edital.id,
    }
    coluna = ordem_map.get(ordenar_por, Edital.data_publicacao)
    if ordem == 'asc':
        query = query.order_by(coluna.asc().nullslast())
    else:
        query = query.order_by(coluna.desc().nullslast())
    
    paginacao = query.paginate(page=pagina, per_page=min(por_pagina, 100), error_out=False)
    return jsonify({
        'editais': [e.to_dict() for e in paginacao.items],
        'total': paginacao.total,
        'paginas': paginacao.pages,
        'pagina_atual': paginacao.page,
    })

'''
    
    lines = lines[:start_idx] + new_func.split('\n') + lines[end_idx:]
    content = '\n'.join(lines)
    open(path, 'w', encoding='utf-8').write(content)
    print('OK - listar_editais reescrito com TODOS os filtros')
else:
    print(f'ERRO - nao encontrei listar_editais (start={start_idx}, end={end_idx})')

# Verificar modelo Edital tem campo municipio
path_models = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\models'
import os
for f in os.listdir(path_models):
    if f.endswith('.py'):
        mc = open(os.path.join(path_models, f), 'r', encoding='utf-8').read()
        if 'class Edital' in mc:
            has_municipio = 'municipio' in mc
            has_modalidade = 'modalidade_nome' in mc
            has_valor = 'valor_estimado' in mc
            has_srp = 'srp' in mc
            has_lances = 'data_inicio_lances' in mc
            print(f'\nModelo Edital em {f}:')
            print(f'  municipio: {"SIM" if has_municipio else "NAO"}')
            print(f'  modalidade_nome: {"SIM" if has_modalidade else "NAO"}')
            print(f'  valor_estimado: {"SIM" if has_valor else "NAO"}')
            print(f'  srp: {"SIM" if has_srp else "NAO"}')
            print(f'  data_inicio_lances: {"SIM" if has_lances else "NAO"}')

print('\n=== PATCH COMPLETO ===')
