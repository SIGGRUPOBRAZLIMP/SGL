"""
SGL - Modelos do Banco de Dados
Todas as entidades principais do sistema
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ============================================================
# USUÁRIOS E AUTENTICAÇÃO
# ============================================================

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    perfil = db.Column(db.String(50), nullable=False, default='cotador')  
    # perfis: admin, gestor, vendedor, cotador
    ativo = db.Column(db.Boolean, default=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                           onupdate=lambda: datetime.now(timezone.utc))
    
    empresa = db.relationship('Empresa', backref='usuarios')
    
    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'perfil': self.perfil,
            'ativo': self.ativo,
            'empresa_id': self.empresa_id,
        }


class Empresa(db.Model):
    """Empresas do Grupo Braz que participam de licitações"""
    __tablename__ = 'empresas'
    
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(300), nullable=False)
    nome_fantasia = db.Column(db.String(300))
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    inscricao_estadual = db.Column(db.String(20))
    endereco = db.Column(db.Text)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(200))
    ativa = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'razao_social': self.razao_social,
            'nome_fantasia': self.nome_fantasia,
            'cnpj': self.cnpj,
            'ativa': self.ativa,
        }


# ============================================================
# CAPTAÇÃO E EDITAIS
# ============================================================

class FiltroProspeccao(db.Model):
    """Filtros configuráveis para busca automática de editais"""
    __tablename__ = 'filtros_prospeccao'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    palavras_chave = db.Column(db.ARRAY(db.String), default=[])
    palavras_exclusao = db.Column(db.ARRAY(db.String), default=[])
    regioes_uf = db.Column(db.ARRAY(db.String), default=[])  # ['SP', 'RJ', 'MG']
    modalidades = db.Column(db.ARRAY(db.Integer), default=[8])  # 8 = Pregão Eletrônico
    valor_minimo = db.Column(db.Numeric(15, 2), nullable=True)
    valor_maximo = db.Column(db.Numeric(15, 2), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    usuario = db.relationship('Usuario', backref='filtros')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'palavras_chave': self.palavras_chave,
            'palavras_exclusao': self.palavras_exclusao,
            'regioes_uf': self.regioes_uf,
            'modalidades': self.modalidades,
            'valor_minimo': float(self.valor_minimo) if self.valor_minimo else None,
            'valor_maximo': float(self.valor_maximo) if self.valor_maximo else None,
            'ativo': self.ativo,
        }


class Edital(db.Model):
    """Edital de licitação captado"""
    __tablename__ = 'editais'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Identificação
    numero_controle_pncp = db.Column(db.String(100), unique=True, nullable=True)
    numero_pregao = db.Column(db.String(50))
    numero_processo = db.Column(db.String(100))
    ano_compra = db.Column(db.Integer)
    sequencial_compra = db.Column(db.Integer)
    
    # Órgão comprador
    orgao_cnpj = db.Column(db.String(18))
    orgao_razao_social = db.Column(db.String(300))
    unidade_codigo = db.Column(db.String(50))
    unidade_nome = db.Column(db.String(300))
    uf = db.Column(db.String(2))
    municipio = db.Column(db.String(200))
    
    # Objeto
    objeto_resumo = db.Column(db.String(500))
    objeto_completo = db.Column(db.Text)
    
    # Classificação
    modalidade_id = db.Column(db.Integer)  # 8=Pregão, 2=Concorrência, etc.
    modalidade_nome = db.Column(db.String(100))
    srp = db.Column(db.Boolean, default=False)  # Sistema Registro de Preços
    tipo_disputa = db.Column(db.String(50))
    
    # Datas
    data_publicacao = db.Column(db.DateTime)
    data_abertura_proposta = db.Column(db.DateTime)
    data_encerramento_proposta = db.Column(db.DateTime)
    data_certame = db.Column(db.DateTime)
    
    # Valores
    valor_estimado = db.Column(db.Numeric(15, 2))
    
    # Origem
    plataforma_origem = db.Column(db.String(50))  # pncp, bll, bnc, licitanet, etc.
    hash_scraper = db.Column(db.String(64), index=True)  # Hash para dedup scrapers
    url_original = db.Column(db.Text)
    link_sistema_origem = db.Column(db.Text)
    
    # Status interno
    status = db.Column(db.String(30), default='captado')
    # captado, em_triagem, aprovado, rejeitado, em_cotacao, em_disputa, finalizado
    
    # Metadados
    situacao_pncp = db.Column(db.String(100))
    informacao_complementar = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    
    # Relacionamentos
    arquivos = db.relationship('EditalArquivo', backref='edital', lazy='dynamic',
                               cascade='all, delete-orphan')
    triagem = db.relationship('Triagem', backref='edital', uselist=False)
    itens_extraidos = db.relationship('ItemEditalExtraido', backref='edital', lazy='dynamic',
                                      cascade='all, delete-orphan')
    
    def to_dict(self, include_arquivos=False):
        data = {
            'id': self.id,
            'numero_controle_pncp': self.numero_controle_pncp,
            'numero_pregao': self.numero_pregao,
            'numero_processo': self.numero_processo,
            'orgao_razao_social': self.orgao_razao_social,
            'orgao_cnpj': self.orgao_cnpj,
            'unidade_nome': self.unidade_nome,
            'uf': self.uf,
            'municipio': self.municipio,
            'objeto_resumo': self.objeto_resumo,
            'modalidade_nome': self.modalidade_nome,
            'srp': self.srp,
            'data_publicacao': self.data_publicacao.isoformat() if self.data_publicacao else None,
            'data_certame': self.data_certame.isoformat() if self.data_certame else None,
            'data_encerramento_proposta': self.data_encerramento_proposta.isoformat() if self.data_encerramento_proposta else None,
            'valor_estimado': float(self.valor_estimado) if self.valor_estimado else None,
            'plataforma_origem': self.plataforma_origem,
            'url_original': self.url_original,
            'link_sistema_origem': self.link_sistema_origem,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_arquivos:
            data['arquivos'] = [a.to_dict() for a in self.arquivos]
        return data


class EditalArquivo(db.Model):
    """Arquivos associados a um edital (PDF, anexos, etc.)"""
    __tablename__ = 'edital_arquivos'
    
    id = db.Column(db.Integer, primary_key=True)
    edital_id = db.Column(db.Integer, db.ForeignKey('editais.id'), nullable=False)
    tipo = db.Column(db.String(50), default='edital')  # edital, anexo, ata, contrato, outro
    nome_arquivo = db.Column(db.String(300))
    url_cloudinary = db.Column(db.Text)
    url_original = db.Column(db.Text)
    tamanho_bytes = db.Column(db.BigInteger)
    mime_type = db.Column(db.String(100))
    texto_extraido = db.Column(db.Text)  # Texto extraído do PDF
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'nome_arquivo': self.nome_arquivo,
            'url_cloudinary': self.url_cloudinary,
            'tamanho_bytes': self.tamanho_bytes,
            'mime_type': self.mime_type,
        }


class ItemEditalExtraido(db.Model):
    """Itens extraídos automaticamente do edital via AI/OCR"""
    __tablename__ = 'itens_edital_extraidos'
    
    id = db.Column(db.Integer, primary_key=True)
    edital_id = db.Column(db.Integer, db.ForeignKey('editais.id'), nullable=False)
    numero_item = db.Column(db.Integer)
    descricao = db.Column(db.Text)
    codigo_referencia = db.Column(db.String(50))
    quantidade = db.Column(db.Numeric(15, 4))
    unidade_compra = db.Column(db.String(50))
    preco_unitario_maximo = db.Column(db.Numeric(15, 4))
    preco_total_maximo = db.Column(db.Numeric(15, 2))
    grupo_lote = db.Column(db.String(50))
    confianca_extracao = db.Column(db.Float)  # 0.0 a 1.0 — confiança da AI na extração
    revisado = db.Column(db.Boolean, default=False)
    metodo_extracao = db.Column(db.String(30))  # claude_api, ocr, pdf_parser, manual
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero_item': self.numero_item,
            'descricao': self.descricao,
            'codigo_referencia': self.codigo_referencia,
            'quantidade': float(self.quantidade) if self.quantidade else None,
            'unidade_compra': self.unidade_compra,
            'preco_unitario_maximo': float(self.preco_unitario_maximo) if self.preco_unitario_maximo else None,
            'preco_total_maximo': float(self.preco_total_maximo) if self.preco_total_maximo else None,
            'grupo_lote': self.grupo_lote,
            'confianca_extracao': self.confianca_extracao,
            'revisado': self.revisado,
            'metodo_extracao': self.metodo_extracao,
        }


# ============================================================
# TRIAGEM
# ============================================================

class Triagem(db.Model):
    """Decisão de triagem sobre um edital"""
    __tablename__ = 'triagens'
    
    id = db.Column(db.Integer, primary_key=True)
    edital_id = db.Column(db.Integer, db.ForeignKey('editais.id'), nullable=False, unique=True)
    usuario_triador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    decisao = db.Column(db.String(20), default='pendente')  # pendente, aprovado, rejeitado
    motivo_rejeicao = db.Column(db.String(200))
    observacoes = db.Column(db.Text)
    prioridade = db.Column(db.String(10), default='media')  # alta, media, baixa
    data_triagem = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    usuario_triador = db.relationship('Usuario', backref='triagens')
    
    def to_dict(self):
        return {
            'id': self.id,
            'edital_id': self.edital_id,
            'decisao': self.decisao,
            'motivo_rejeicao': self.motivo_rejeicao,
            'observacoes': self.observacoes,
            'prioridade': self.prioridade,
            'data_triagem': self.data_triagem.isoformat() if self.data_triagem else None,
            'triador': self.usuario_triador.nome if self.usuario_triador else None,
        }


# ============================================================
# PROCESSOS E COTAÇÃO
# ============================================================

class Processo(db.Model):
    """Processo de licitação em andamento"""
    __tablename__ = 'processos'
    
    id = db.Column(db.Integer, primary_key=True)
    edital_id = db.Column(db.Integer, db.ForeignKey('editais.id'), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'))
    cotador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    nome_pasta = db.Column(db.String(500))  # Ex: "PE 001/2025 - Proc 123 - Material Escritório - 15/03/2025"
    status = db.Column(db.String(30), default='aguardando')
    # aguardando, em_cotacao, cotado, em_analise, pronto, em_disputa, ganho_parcial, ganho_total, perdido, finalizado
    
    margem_minima = db.Column(db.Numeric(5, 2), default=15.00)  # % margem mínima
    
    data_atribuicao = db.Column(db.DateTime)
    data_limite = db.Column(db.DateTime)  # Prazo para finalizar cotação
    prioridade = db.Column(db.String(10), default='media')
    observacoes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    
    edital = db.relationship('Edital', backref='processos')
    empresa = db.relationship('Empresa', backref='processos')
    cotador = db.relationship('Usuario', backref='processos')
    itens = db.relationship('ItemEdital', backref='processo', lazy='dynamic',
                            cascade='all, delete-orphan')
    historico = db.relationship('ProcessoHistorico', backref='processo', lazy='dynamic',
                                cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'edital_id': self.edital_id,
            'empresa_id': self.empresa_id,
            'cotador': self.cotador.nome if self.cotador else None,
            'nome_pasta': self.nome_pasta,
            'status': self.status,
            'margem_minima': float(self.margem_minima) if self.margem_minima else None,
            'data_limite': self.data_limite.isoformat() if self.data_limite else None,
            'prioridade': self.prioridade,
            'total_itens': self.itens.count(),
        }


class ProcessoHistorico(db.Model):
    """Histórico de mudanças de status do processo"""
    __tablename__ = 'processos_historico'
    
    id = db.Column(db.Integer, primary_key=True)
    processo_id = db.Column(db.Integer, db.ForeignKey('processos.id'), nullable=False)
    status_anterior = db.Column(db.String(30))
    status_novo = db.Column(db.String(30), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    observacao = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Fornecedor(db.Model):
    """Fornecedores para cotação"""
    __tablename__ = 'fornecedores'
    
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(300), nullable=False)
    nome_fantasia = db.Column(db.String(300))
    cnpj = db.Column(db.String(18), unique=True)
    email = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    contato_nome = db.Column(db.String(200))
    segmentos = db.Column(db.ARRAY(db.String), default=[])
    observacoes = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'razao_social': self.razao_social,
            'nome_fantasia': self.nome_fantasia,
            'cnpj': self.cnpj,
            'email': self.email,
            'telefone': self.telefone,
            'contato_nome': self.contato_nome,
            'segmentos': self.segmentos,
            'ativo': self.ativo,
        }


class ItemEdital(db.Model):
    """Itens do edital no processo de cotação"""
    __tablename__ = 'itens_edital'
    
    id = db.Column(db.Integer, primary_key=True)
    processo_id = db.Column(db.Integer, db.ForeignKey('processos.id'), nullable=False)
    numero_item = db.Column(db.Integer)
    descricao = db.Column(db.Text, nullable=False)
    codigo_referencia = db.Column(db.String(50))
    quantidade = db.Column(db.Numeric(15, 4), nullable=False)
    unidade_compra = db.Column(db.String(50))
    preco_unitario_maximo = db.Column(db.Numeric(15, 4))
    preco_total_maximo = db.Column(db.Numeric(15, 2))
    grupo_lote = db.Column(db.String(50))
    
    # Resultado da análise de viabilidade
    status = db.Column(db.String(20), default='pendente')
    # pendente, aprovado, reprovado, sem_cotacao
    melhor_custo = db.Column(db.Numeric(15, 4))
    preco_venda = db.Column(db.Numeric(15, 4))
    margem_real = db.Column(db.Numeric(5, 2))
    fornecedor_selecionado_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'))
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    fornecedor_selecionado = db.relationship('Fornecedor')
    cotacoes = db.relationship('CotacaoFornecedor', backref='item_edital', lazy='dynamic',
                               cascade='all, delete-orphan')
    
    def to_dict(self, include_cotacoes=False):
        data = {
            'id': self.id,
            'numero_item': self.numero_item,
            'descricao': self.descricao,
            'codigo_referencia': self.codigo_referencia,
            'quantidade': float(self.quantidade) if self.quantidade else None,
            'unidade_compra': self.unidade_compra,
            'preco_unitario_maximo': float(self.preco_unitario_maximo) if self.preco_unitario_maximo else None,
            'preco_total_maximo': float(self.preco_total_maximo) if self.preco_total_maximo else None,
            'status': self.status,
            'melhor_custo': float(self.melhor_custo) if self.melhor_custo else None,
            'preco_venda': float(self.preco_venda) if self.preco_venda else None,
            'margem_real': float(self.margem_real) if self.margem_real else None,
            'fornecedor_selecionado': self.fornecedor_selecionado.to_dict() if self.fornecedor_selecionado else None,
        }
        if include_cotacoes:
            data['cotacoes'] = [c.to_dict() for c in self.cotacoes]
        return data


class CotacaoFornecedor(db.Model):
    """Cotação de um fornecedor para um item do edital"""
    __tablename__ = 'cotacoes_fornecedor'
    
    id = db.Column(db.Integer, primary_key=True)
    item_edital_id = db.Column(db.Integer, db.ForeignKey('itens_edital.id'), nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'), nullable=False)
    marca = db.Column(db.String(200))
    codigo_produto = db.Column(db.String(100))
    preco_unitario = db.Column(db.Numeric(15, 4), nullable=False)
    preco_total = db.Column(db.Numeric(15, 2))
    observacoes = db.Column(db.Text)
    selecionado = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    fornecedor = db.relationship('Fornecedor', backref='cotacoes')
    
    def to_dict(self):
        return {
            'id': self.id,
            'fornecedor': self.fornecedor.to_dict() if self.fornecedor else None,
            'marca': self.marca,
            'codigo_produto': self.codigo_produto,
            'preco_unitario': float(self.preco_unitario) if self.preco_unitario else None,
            'preco_total': float(self.preco_total) if self.preco_total else None,
            'observacoes': self.observacoes,
            'selecionado': self.selecionado,
        }


# ============================================================
# DISPUTA E PÓS-VENDA
# ============================================================

class Disputa(db.Model):
    """Registro de participação em disputa/certame"""
    __tablename__ = 'disputas'
    
    id = db.Column(db.Integer, primary_key=True)
    processo_id = db.Column(db.Integer, db.ForeignKey('processos.id'), nullable=False)
    data_inicio = db.Column(db.DateTime)
    data_fim = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='agendada')
    # agendada, em_andamento, finalizada, suspensa, cancelada
    plataforma = db.Column(db.String(50))
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    processo = db.relationship('Processo', backref='disputas')
    lances = db.relationship('Lance', backref='disputa', lazy='dynamic',
                             cascade='all, delete-orphan')


class Lance(db.Model):
    """Registro de lances durante a disputa"""
    __tablename__ = 'lances'
    
    id = db.Column(db.Integer, primary_key=True)
    disputa_id = db.Column(db.Integer, db.ForeignKey('disputas.id'), nullable=False)
    item_edital_id = db.Column(db.Integer, db.ForeignKey('itens_edital.id'), nullable=False)
    valor_lance = db.Column(db.Numeric(15, 4), nullable=False)
    posicao = db.Column(db.Integer)
    melhor_lance_concorrente = db.Column(db.Numeric(15, 4))
    resultado = db.Column(db.String(20))  # ganhou, perdeu, empate, em_andamento
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    item_edital = db.relationship('ItemEdital', backref='lances')


class VendaReajustada(db.Model):
    """Planilha de venda reajustada após ganhar itens"""
    __tablename__ = 'vendas_reajustadas'
    
    id = db.Column(db.Integer, primary_key=True)
    processo_id = db.Column(db.Integer, db.ForeignKey('processos.id'), nullable=False)
    disputa_id = db.Column(db.Integer, db.ForeignKey('disputas.id'))
    data_geracao = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='rascunho')  # rascunho, finalizada, enviada
    valor_total = db.Column(db.Numeric(15, 2))
    observacoes = db.Column(db.Text)
    
    processo = db.relationship('Processo', backref='vendas')
    itens = db.relationship('ItemVenda', backref='venda', lazy='dynamic',
                            cascade='all, delete-orphan')


class ItemVenda(db.Model):
    """Itens da venda reajustada"""
    __tablename__ = 'itens_venda'
    
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas_reajustadas.id'), nullable=False)
    item_edital_id = db.Column(db.Integer, db.ForeignKey('itens_edital.id'))
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'))
    marca = db.Column(db.String(200))
    codigo_produto = db.Column(db.String(100))
    quantidade = db.Column(db.Numeric(15, 4))
    custo_unitario = db.Column(db.Numeric(15, 4))
    margem_aplicada = db.Column(db.Numeric(5, 2))
    preco_venda_unitario = db.Column(db.Numeric(15, 4))
    preco_venda_total = db.Column(db.Numeric(15, 2))
    
    fornecedor = db.relationship('Fornecedor')
    item_edital = db.relationship('ItemEdital')


# ============================================================
# INTEGRAÇÃO SIG
# ============================================================

class IntegracaoSIG(db.Model):
    """Controle de sincronização com o SIG"""
    __tablename__ = 'integracao_sig'
    
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas_reajustadas.id'))
    item_venda_id = db.Column(db.Integer, db.ForeignKey('itens_venda.id'))
    sincronizado = db.Column(db.Boolean, default=False)
    data_sincronizacao = db.Column(db.DateTime)
    sig_contrato_id = db.Column(db.Integer)
    sig_fornecedor_id = db.Column(db.Integer)
    erro_sincronizacao = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


# ============================================================
# LOG DE ATIVIDADES
# ============================================================

class LogAtividade(db.Model):
    """Log de atividades do sistema"""
    __tablename__ = 'logs_atividade'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    acao = db.Column(db.String(100), nullable=False)
    entidade = db.Column(db.String(50))
    entidade_id = db.Column(db.Integer)
    detalhes = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
