"""
SGL - Rotas da API REST
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)

from ..models.database import (
    db, Usuario, Empresa, Edital, EditalArquivo, 
    ItemEditalExtraido, Triagem, FiltroProspeccao,
    Processo, Fornecedor, ItemEdital, CotacaoFornecedor
)
from ..services.captacao_service import CaptacaoService

api_bp = Blueprint('api', __name__)


# ============================================================
# AUTH
# ============================================================

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Autenticação de usuário → JWT"""
    data = request.get_json()
    email = data.get('email')
    senha = data.get('senha')
    
    if not email or not senha:
        return jsonify({'error': 'Email e senha são obrigatórios'}), 400
    
    usuario = Usuario.query.filter_by(email=email, ativo=True).first()
    if not usuario or not usuario.verificar_senha(senha):
        return jsonify({'error': 'Credenciais inválidas'}), 401
    
    access_token = create_access_token(
        identity=str(usuario.id),
        additional_claims={'perfil': usuario.perfil, 'nome': usuario.nome}
    )
    refresh_token = create_refresh_token(identity=str(usuario.id))
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'usuario': usuario.to_dict()
    })


@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Registro de novo usuário (somente admin)"""
    data = request.get_json()
    
    if Usuario.query.filter_by(email=data.get('email')).first():
        return jsonify({'error': 'Email já cadastrado'}), 409
    
    usuario = Usuario(
        nome=data['nome'],
        email=data['email'],
        perfil=data.get('perfil', 'cotador'),
        empresa_id=data.get('empresa_id')
    )
    usuario.set_senha(data['senha'])
    
    db.session.add(usuario)
    db.session.commit()
    
    return jsonify(usuario.to_dict()), 201


# ============================================================
# EDITAIS (Captação + Consulta)
# ============================================================

@api_bp.route('/editais', methods=['GET'])
@jwt_required()
def listar_editais():
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
    paginacao = query.paginate(page=pagina, per_page=min(por_pagina, 100), error_out=False)
    
    return jsonify({
        'editais': [e.to_dict() for e in paginacao.items],
        'total': paginacao.total,
        'paginas': paginacao.pages,
        'pagina_atual': paginacao.page,
    })


@api_bp.route('/editais/<int:edital_id>', methods=['GET'])
@jwt_required()
def obter_edital(edital_id):
    """Detalhes completos de um edital"""
    edital = Edital.query.get_or_404(edital_id)
    data = edital.to_dict(include_arquivos=True)
    
    # Incluir triagem
    if edital.triagem:
        data['triagem'] = edital.triagem.to_dict()
    
    # Incluir itens extraídos via AI
    itens = edital.itens_extraidos.all()
    if itens:
        data['itens_extraidos'] = [i.to_dict() for i in itens]
    
    return jsonify(data)


@api_bp.route('/editais/captar', methods=['POST'])
@jwt_required()
def executar_captacao():
    """
    Executa captação manual de editais via PNCP.
    Corpo: { periodo_dias, data_inicial, data_final, ufs, modalidades }
    """
    data = request.get_json() or {}
    
    service = CaptacaoService(current_app.config)
    resultado_pncp = service.executar_captacao(
        periodo_dias=data.get('periodo_dias'),
        data_inicial=data.get('data_inicial'),
        data_final=data.get('data_final'),
        ufs=data.get('ufs'),
        modalidades=data.get('modalidades'),
        filtros_ids=data.get('filtros_ids')
    )
    periodo = data.get('periodo_dias') or 3
    ufs_busca = data.get('ufs') or ['RJ', 'SP', 'MG', 'ES']
    resultado_bbmnet = {}
    try:
        from ..services.bbmnet_integration import executar_captacao_bbmnet as captar_bbmnet
        resultado_bbmnet = captar_bbmnet(app_config=current_app.config, periodo_dias=periodo, ufs=ufs_busca)
    except Exception as e:
        resultado_bbmnet = {'erro': str(e)}
    resultado_licitar = {}
    try:
        from ..services.licitardigital_integration import executar_captacao_licitardigital as captar_licitar
        resultado_licitar = captar_licitar(app_config=current_app.config, periodo_dias=periodo)
    except Exception as e:
        resultado_licitar = {'erro': str(e)}
    resultado_pncp['bbmnet'] = resultado_bbmnet
    resultado_pncp['licitardigital'] = resultado_licitar
    resultado_pncp['total_geral'] = resultado_pncp.get('novos_salvos', 0) + resultado_bbmnet.get('novos_salvos', 0) + resultado_licitar.get('novos_salvos', 0)
    return jsonify(resultado_pncp)

# CAPTACAO PNCP (manual - separado)
@api_bp.route('/editais/captar-pncp', methods=['POST'])
@jwt_required()
def executar_captacao_pncp_only():
    data = request.get_json() or {}
    try:
        service = CaptacaoService(current_app.config)
        resultado = service.executar_captacao(
            periodo_dias=data.get('periodo_dias', 3),
            ufs=data.get('ufs'),
            modalidades=data.get('modalidades'),
            filtros_ids=data.get('filtros_ids')
        )
        return jsonify({'sucesso': True, 'plataforma': 'pncp', **resultado}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# CAPTACAO BBMNET (manual)
@api_bp.route('/editais/captar-bbmnet', methods=['POST'])
@jwt_required()
def executar_captacao_bbmnet():
    data = request.get_json() or {}
    periodo_dias = data.get('periodo_dias', 7)
    ufs = data.get('ufs', ['RJ', 'SP', 'MG', 'ES'])
    try:
        from ..services.bbmnet_integration import executar_captacao_bbmnet as captar_bbmnet
        resultado = captar_bbmnet(
            app_config=current_app.config,
            periodo_dias=periodo_dias,
            ufs=ufs,
        )
        return jsonify({'sucesso': True, 'plataforma': 'bbmnet', 'stats': resultado}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500



# CAPTACAO LICITAR DIGITAL (manual)
@api_bp.route('/editais/captar-licitar', methods=['POST'])
@jwt_required()
def executar_captacao_licitar_only():
    data = request.get_json() or {}
    periodo_dias = data.get('periodo_dias', 7)
    try:
        from ..services.licitardigital_integration import executar_captacao_licitardigital as captar_licitar
        resultado = captar_licitar(app_config=current_app.config, periodo_dias=periodo_dias)
        return jsonify({'sucesso': True, 'plataforma': 'licitardigital', **resultado}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@api_bp.route('/scheduler/status', methods=['GET'])
@jwt_required()
def scheduler_status():
    """Retorna status do agendador de captação automática."""
    try:
        from ..scheduler import scheduler
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'nome': job.name,
                'proximo_disparo': str(job.next_run_time) if job.next_run_time else None,
            })
        return jsonify({
            'ativo': scheduler.running,
            'jobs': jobs,
        })
    except Exception as e:
        return jsonify({'ativo': False, 'erro': str(e)})


# ============================================================
# EXTRAÇÃO AI DE ITENS
# ============================================================

@api_bp.route('/editais/<int:edital_id>/extrair-itens', methods=['POST'])
@jwt_required()
def extrair_itens_edital(edital_id):
    """Extrai itens do edital usando Claude AI"""
    service = CaptacaoService(current_app.config)
    resultado = service.extrair_itens_edital(edital_id)
    
    if 'erro' in resultado:
        return jsonify(resultado), 400
    return jsonify(resultado)


@api_bp.route('/editais/<int:edital_id>/classificar', methods=['POST'])
@jwt_required()
def classificar_edital(edital_id):
    """Classifica relevância do edital via Claude AI"""
    data = request.get_json() or {}
    segmentos = data.get('segmentos', [])
    
    if not segmentos:
        return jsonify({'error': 'Informe os segmentos de interesse'}), 400
    
    service = CaptacaoService(current_app.config)
    resultado = service.classificar_edital(edital_id, segmentos)
    
    return jsonify(resultado)


@api_bp.route('/editais/<int:edital_id>/resumir', methods=['POST'])
@jwt_required()
def resumir_edital(edital_id):
    """Gera resumo executivo do edital via Claude AI"""
    service = CaptacaoService(current_app.config)
    resultado = service.resumir_edital(edital_id)
    
    if 'erro' in resultado:
        return jsonify(resultado), 400
    return jsonify(resultado)


# ============================================================
# TRIAGEM
# ============================================================

@api_bp.route('/triagem', methods=['GET'])
@jwt_required()
def listar_triagem():
    """Lista editais pendentes de triagem"""
    status = request.args.get('status', 'pendente')
    
    query = db.session.query(Edital, Triagem).join(
        Triagem, Edital.id == Triagem.edital_id
    ).filter(Triagem.decisao == status)
    
    query = query.order_by(Triagem.prioridade.desc(), Edital.data_publicacao.desc())
    
    resultados = []
    for edital, triagem in query.all():
        item = edital.to_dict()
        item['triagem'] = triagem.to_dict()
        resultados.append(item)
    
    return jsonify({'editais': resultados, 'total': len(resultados)})


@api_bp.route('/triagem/<int:edital_id>', methods=['PUT'])
@jwt_required()
def decidir_triagem(edital_id):
    """Registra decisão de triagem"""
    data = request.get_json()
    usuario_id = int(get_jwt_identity())
    
    triagem = Triagem.query.filter_by(edital_id=edital_id).first()
    if not triagem:
        return jsonify({'error': 'Triagem não encontrada'}), 404
    
    triagem.decisao = data.get('decisao', triagem.decisao)
    triagem.motivo_rejeicao = data.get('motivo_rejeicao')
    triagem.observacoes = data.get('observacoes')
    triagem.prioridade = data.get('prioridade', triagem.prioridade)
    triagem.usuario_triador_id = usuario_id
    triagem.data_triagem = datetime.now(timezone.utc)
    
    # Atualizar status do edital
    edital = Edital.query.get(edital_id)
    if data.get('decisao') == 'aprovado':
        edital.status = 'aprovado'
    elif data.get('decisao') == 'rejeitado':
        edital.status = 'rejeitado'
    
    db.session.commit()
    return jsonify(triagem.to_dict())


# ============================================================
# FILTROS DE PROSPECÇÃO
# ============================================================

@api_bp.route('/filtros', methods=['GET'])
@jwt_required()
def listar_filtros():
    filtros = FiltroProspeccao.query.filter_by(ativo=True).all()
    return jsonify([f.to_dict() for f in filtros])


@api_bp.route('/filtros', methods=['POST'])
@jwt_required()
def criar_filtro():
    data = request.get_json()
    usuario_id = int(get_jwt_identity())
    
    filtro = FiltroProspeccao(
        nome=data['nome'],
        palavras_chave=data.get('palavras_chave', []),
        palavras_exclusao=data.get('palavras_exclusao', []),
        regioes_uf=data.get('regioes_uf', []),
        modalidades=data.get('modalidades', [8]),
        valor_minimo=data.get('valor_minimo'),
        valor_maximo=data.get('valor_maximo'),
        ativo=True,
        usuario_id=usuario_id
    )
    
    db.session.add(filtro)
    db.session.commit()
    return jsonify(filtro.to_dict()), 201


# ============================================================
# FORNECEDORES
# ============================================================

@api_bp.route('/fornecedores', methods=['GET'])
@jwt_required()
def listar_fornecedores():
    busca = request.args.get('busca')
    query = Fornecedor.query.filter_by(ativo=True)
    
    if busca:
        query = query.filter(
            db.or_(
                Fornecedor.razao_social.ilike(f'%{busca}%'),
                Fornecedor.nome_fantasia.ilike(f'%{busca}%'),
                Fornecedor.cnpj.ilike(f'%{busca}%')
            )
        )
    
    fornecedores = query.order_by(Fornecedor.razao_social).all()
    return jsonify([f.to_dict() for f in fornecedores])


@api_bp.route('/fornecedores', methods=['POST'])
@jwt_required()
def criar_fornecedor():
    data = request.get_json()
    
    if Fornecedor.query.filter_by(cnpj=data.get('cnpj')).first():
        return jsonify({'error': 'CNPJ já cadastrado'}), 409
    
    fornecedor = Fornecedor(
        razao_social=data['razao_social'],
        nome_fantasia=data.get('nome_fantasia'),
        cnpj=data.get('cnpj'),
        email=data.get('email'),
        telefone=data.get('telefone'),
        contato_nome=data.get('contato_nome'),
        segmentos=data.get('segmentos', []),
        observacoes=data.get('observacoes')
    )
    
    db.session.add(fornecedor)
    db.session.commit()
    return jsonify(fornecedor.to_dict()), 201


@api_bp.route('/fornecedores/<int:id>', methods=['PUT'])
@jwt_required()
def atualizar_fornecedor(id):
    fornecedor = Fornecedor.query.get_or_404(id)
    data = request.get_json()
    
    for campo in ['razao_social', 'nome_fantasia', 'email', 'telefone', 
                   'contato_nome', 'segmentos', 'observacoes', 'ativo']:
        if campo in data:
            setattr(fornecedor, campo, data[campo])
    
    db.session.commit()
    return jsonify(fornecedor.to_dict())


# ============================================================
# PROCESSOS
# ============================================================

@api_bp.route('/processos', methods=['GET'])
@jwt_required()
def listar_processos():
    status = request.args.get('status')
    cotador_id = request.args.get('cotador_id', type=int)
    
    query = Processo.query
    if status:
        query = query.filter(Processo.status == status)
    if cotador_id:
        query = query.filter(Processo.cotador_id == cotador_id)
    
    query = query.order_by(Processo.prioridade.desc(), Processo.data_limite.asc().nullslast())
    processos = query.all()
    
    return jsonify([p.to_dict() for p in processos])


@api_bp.route('/processos', methods=['POST'])
@jwt_required()
def criar_processo():
    """Cria processo a partir de um edital aprovado"""
    data = request.get_json()
    
    edital = Edital.query.get_or_404(data['edital_id'])
    
    # Gerar nome da pasta: PE 001/2025 - Proc 123 - Objeto - Data
    data_certame_str = ''
    if edital.data_certame:
        data_certame_str = edital.data_certame.strftime('%d/%m/%Y')
    
    nome_pasta = (
        f"{edital.modalidade_nome or 'PE'} {edital.numero_pregao or ''} - "
        f"Proc {edital.numero_processo or ''} - "
        f"{(edital.objeto_resumo or '')[:80]} - "
        f"{data_certame_str}"
    ).strip(' -')
    
    processo = Processo(
        edital_id=edital.id,
        empresa_id=data.get('empresa_id'),
        cotador_id=data.get('cotador_id'),
        nome_pasta=nome_pasta,
        status='aguardando',
        margem_minima=data.get('margem_minima', 15.0),
        data_atribuicao=datetime.now(timezone.utc) if data.get('cotador_id') else None,
        data_limite=data.get('data_limite'),
        prioridade=data.get('prioridade', 'media'),
        observacoes=data.get('observacoes')
    )
    
    db.session.add(processo)
    edital.status = 'em_cotacao'
    db.session.commit()
    
    return jsonify(processo.to_dict()), 201


@api_bp.route('/processos/<int:processo_id>/importar-itens-ai', methods=['POST'])
@jwt_required()
def importar_itens_ai(processo_id):
    """
    Importa itens extraídos via AI para o processo de cotação.
    Move itens de ItemEditalExtraido → ItemEdital
    """
    processo = Processo.query.get_or_404(processo_id)
    edital = processo.edital
    
    itens_extraidos = edital.itens_extraidos.filter_by(revisado=True).all()
    if not itens_extraidos:
        # Se não há itens revisados, usar todos
        itens_extraidos = edital.itens_extraidos.all()
    
    if not itens_extraidos:
        return jsonify({'error': 'Nenhum item extraído encontrado. Execute a extração AI primeiro.'}), 400
    
    importados = 0
    for item_ai in itens_extraidos:
        item = ItemEdital(
            processo_id=processo_id,
            numero_item=item_ai.numero_item,
            descricao=item_ai.descricao,
            codigo_referencia=item_ai.codigo_referencia,
            quantidade=item_ai.quantidade or 0,
            unidade_compra=item_ai.unidade_compra or 'UN',
            preco_unitario_maximo=item_ai.preco_unitario_maximo,
            preco_total_maximo=item_ai.preco_total_maximo,
            grupo_lote=item_ai.grupo_lote,
            status='pendente'
        )
        db.session.add(item)
        importados += 1
    
    processo.status = 'em_cotacao'
    db.session.commit()
    
    return jsonify({
        'mensagem': f'{importados} itens importados para cotação',
        'itens_importados': importados
    })


# ============================================================
# ANÁLISE DE VIABILIDADE
# ============================================================

@api_bp.route('/processos/<int:processo_id>/analisar-viabilidade', methods=['POST'])
@jwt_required()
def analisar_viabilidade(processo_id):
    """
    Executa análise de viabilidade automática para todos os itens do processo.
    Compara melhor preço de fornecedor + margem vs preço máximo.
    """
    processo = Processo.query.get_or_404(processo_id)
    margem = float(processo.margem_minima or 15)
    
    itens = processo.itens.all()
    resultados = {'aprovados': 0, 'reprovados': 0, 'sem_cotacao': 0, 'total': len(itens)}
    
    for item in itens:
        cotacoes = item.cotacoes.all()
        
        if not cotacoes:
            item.status = 'sem_cotacao'
            resultados['sem_cotacao'] += 1
            continue
        
        # Encontrar melhor preço
        melhor = min(cotacoes, key=lambda c: float(c.preco_unitario))
        custo = float(melhor.preco_unitario)
        preco_venda = custo * (1 + margem / 100)
        preco_max = float(item.preco_unitario_maximo or 0)
        
        item.melhor_custo = custo
        item.preco_venda = preco_venda
        item.fornecedor_selecionado_id = melhor.fornecedor_id
        
        if preco_max > 0:
            item.margem_real = ((preco_max / custo) - 1) * 100
            
            if preco_venda <= preco_max:
                item.status = 'aprovado'
                resultados['aprovados'] += 1
            else:
                item.status = 'reprovado'
                resultados['reprovados'] += 1
        else:
            item.status = 'pendente'
    
    # Calcular valor total estimado
    valor_total = sum(
        float(i.preco_venda or 0) * float(i.quantidade or 0)
        for i in itens if i.status == 'aprovado'
    )
    resultados['valor_total_estimado'] = valor_total
    
    processo.status = 'em_analise'
    db.session.commit()
    
    return jsonify(resultados)


# ============================================================
# DASHBOARD / STATS
# ============================================================

@api_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    """Estatísticas gerais para o dashboard"""
    total_editais = Edital.query.count()
    editais_pendentes = Edital.query.filter_by(status='captado').count()
    editais_aprovados = Edital.query.filter_by(status='aprovado').count()
    editais_em_cotacao = Edital.query.filter_by(status='em_cotacao').count()
    
    total_processos = Processo.query.count()
    processos_ativos = Processo.query.filter(
        Processo.status.in_(['aguardando', 'em_cotacao', 'cotado', 'em_analise', 'pronto', 'em_disputa'])
    ).count()
    
    total_fornecedores = Fornecedor.query.filter_by(ativo=True).count()
    
    return jsonify({
        'editais': {
            'total': total_editais,
            'pendentes_triagem': editais_pendentes,
            'aprovados': editais_aprovados,
            'em_cotacao': editais_em_cotacao,
        },
        'processos': {
            'total': total_processos,
            'ativos': processos_ativos,
        },
        'fornecedores': {
            'total': total_fornecedores,
        }
    })
