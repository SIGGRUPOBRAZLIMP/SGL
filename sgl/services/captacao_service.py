"""
SGL - Serviço de Captação de Editais
Combina: API PNCP + Filtros Inteligentes + Claude AI + Storage
"""
import hashlib
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Optional

from ..models.database import (
    db, Edital, EditalArquivo, ItemEditalExtraido, 
    FiltroProspeccao, Triagem
)
from .pncp_client import PNCPClient, formatar_data_pncp
from .edital_interpreter import EditalInterpreter, PDFTextExtractor

logger = logging.getLogger(__name__)


class CaptacaoService:
    """
    Serviço principal de captação automática de editais.
    Orquestra: busca no PNCP → filtragem → download → extração AI → persistência.
    """
    
    def __init__(self, config: dict):
        self.pncp = PNCPClient(
            timeout=config.get('PNCP_API_TIMEOUT', 30),
            max_retries=config.get('PNCP_API_MAX_RETRIES', 3),
            page_size=config.get('PNCP_API_PAGE_SIZE', 50)
        )
        
        # Claude AI — interpretação de editais
        api_key = config.get('ANTHROPIC_API_KEY', '')
        if api_key:
            self.interpreter = EditalInterpreter(
                api_key=api_key,
                model=config.get('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929'),
                max_tokens=config.get('CLAUDE_MAX_TOKENS', 8000)
            )
        else:
            self.interpreter = None
            logger.warning("ANTHROPIC_API_KEY não configurada — extração AI desabilitada")
    
    # =========================================================
    # CAPTAÇÃO PRINCIPAL
    # =========================================================
    
    def executar_captacao(
        self,
        data_inicial: Optional[str] = None,
        data_final: Optional[str] = None,
        ufs: Optional[list[str]] = None,
        modalidades: Optional[list[int]] = None,
        filtros_ids: Optional[list[int]] = None
    ) -> dict:
        """
        Executa ciclo completo de captação.
        
        Fluxo:
        1. Buscar contratações no PNCP
        2. Filtrar por critérios configurados
        3. Verificar duplicidades
        4. Salvar editais novos
        5. Baixar documentos
        6. Extrair itens via AI (se configurado)
        7. Criar triagem pendente
        
        Returns:
            dict com estatísticas da captação
        """
        stats = {
            'total_encontrados': 0,
            'novos_salvos': 0,
            'duplicados': 0,
            'filtrados': 0,
            'erros': 0,
            'itens_extraidos': 0,
        }
        
        # Defaults
        hoje = datetime.now()
        if not data_inicial:
            data_inicial = formatar_data_pncp(hoje)
        if not data_final:
            data_final = formatar_data_pncp(hoje)
        if not modalidades:
            modalidades = [8]  # Pregão Eletrônico por padrão
        
        # Carregar filtros de prospecção ativos
        filtros = self._carregar_filtros(filtros_ids)
        
        # Para cada combinação UF + modalidade
        ufs_busca = ufs or [None]  # None = todas as UFs
        
        for uf in ufs_busca:
            for modalidade in modalidades:
                try:
                    contratacoes = self.pncp.buscar_todas_contratacoes(
                        data_inicial=data_inicial,
                        data_final=data_final,
                        modalidade=modalidade,
                        uf=uf,
                        max_paginas=10
                    )
                    
                    stats['total_encontrados'] += len(contratacoes)
                    
                    for contratacao in contratacoes:
                        resultado = self._processar_contratacao(contratacao, filtros)
                        stats[resultado] += 1
                        
                except Exception as e:
                    logger.error(f"Erro na captação UF={uf} MOD={modalidade}: {e}")
                    stats['erros'] += 1
        
        logger.info(f"Captação finalizada: {stats}")
        return stats
    
    def _processar_contratacao(self, contratacao: dict, filtros: list) -> str:
        """
        Processa uma contratação individual do PNCP.
        
        Returns:
            String indicando resultado: 'novos_salvos', 'duplicados', 'filtrados', 'erros'
        """
        try:
            # 1. Extrair número de controle PNCP
            numero_pncp = contratacao.get('numeroControlePNCP')
            if not numero_pncp:
                return 'erros'
            
            # 2. Verificar duplicidade
            existente = Edital.query.filter_by(numero_controle_pncp=numero_pncp).first()
            if existente:
                return 'duplicados'
            
            # 3. Aplicar filtros
            if filtros and not self._contratacao_passa_filtros(contratacao, filtros):
                return 'filtrados'
            
            # 4. Criar edital no banco
            edital = self._criar_edital(contratacao)
            db.session.add(edital)
            db.session.flush()  # Para ter o ID
            
            # 5. Criar triagem pendente
            triagem = Triagem(
                edital_id=edital.id,
                decisao='pendente',
                prioridade=self._calcular_prioridade(contratacao)
            )
            db.session.add(triagem)
            
            # 6. Buscar e salvar arquivos (async em produção via Celery)
            # Arquivos processados depois via Celery (evita timeout)
            # self._processar_arquivos(edital, contratacao)
            
            db.session.commit()
            
            logger.info(f"Novo edital salvo: {numero_pncp} | {edital.objeto_resumo[:80]}")
            return 'novos_salvos'
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao processar contratação: {e}")
            return 'erros'
    
    # =========================================================
    # EXTRAÇÃO AI DE ITENS
    # =========================================================
    
    def extrair_itens_edital(self, edital_id: int) -> dict:
        """
        Extrai itens de um edital usando Claude AI.
        Pode ser chamado manualmente ou via Celery task.
        
        Returns:
            dict com resultado da extração
        """
        if not self.interpreter:
            return {'erro': 'Claude API não configurada'}
        
        edital = Edital.query.get(edital_id)
        if not edital:
            return {'erro': 'Edital não encontrado'}
        
        # Buscar arquivo principal do edital
        arquivo_edital = edital.arquivos.filter_by(tipo='edital').first()
        if not arquivo_edital:
            arquivo_edital = edital.arquivos.first()
        
        if not arquivo_edital or not arquivo_edital.texto_extraido:
            # Tentar extrair texto do PDF
            if arquivo_edital and arquivo_edital.url_cloudinary:
                texto = self._baixar_e_extrair_texto(arquivo_edital.url_cloudinary)
                if texto:
                    arquivo_edital.texto_extraido = texto
                    db.session.commit()
                else:
                    return {'erro': 'Não foi possível extrair texto do PDF'}
            else:
                # Fallback: usar texto do objeto
                texto_obj = edital.objeto_completo or edital.objeto_resumo or ''
                if not texto_obj:
                    return {'erro': 'Nenhum texto disponível para análise'}
                class FakeArquivo:
                    texto_extraido = texto_obj
                arquivo_edital = FakeArquivo()
        
        # Preparar contexto
        contexto = (
            f"Pregão {edital.numero_pregao or ''} | "
            f"Processo {edital.numero_processo or ''} | "
            f"Órgão: {edital.orgao_razao_social or ''} | "
            f"UF: {edital.uf or ''}"
        )
        
        # Chamar Claude AI para extração
        resultado = self.interpreter.extrair_itens(
            texto_edital=arquivo_edital.texto_extraido,
            contexto=contexto
        )
        
        # Salvar itens extraídos no banco
        itens_salvos = 0
        for item_data in resultado.get('itens', []):
            item = ItemEditalExtraido(
                edital_id=edital_id,
                numero_item=item_data.get('numero_item'),
                descricao=item_data.get('descricao', ''),
                codigo_referencia=item_data.get('codigo_referencia'),
                quantidade=item_data.get('quantidade'),
                unidade_compra=item_data.get('unidade_compra', 'UN'),
                preco_unitario_maximo=item_data.get('preco_unitario_maximo'),
                preco_total_maximo=item_data.get('preco_total_maximo'),
                grupo_lote=item_data.get('grupo_lote'),
                confianca_extracao=item_data.get('confianca', 0.5),
                metodo_extracao='claude_api',
                revisado=False
            )
            db.session.add(item)
            itens_salvos += 1
        
        db.session.commit()
        
        logger.info(f"Extração AI: {itens_salvos} itens salvos para edital {edital_id}")
        
        resultado['itens_salvos'] = itens_salvos
        return resultado
    
    def classificar_edital(self, edital_id: int, segmentos: list[str]) -> dict:
        """Classifica relevância de um edital usando Claude AI."""
        if not self.interpreter:
            return {'erro': 'Claude API não configurada'}
        
        edital = Edital.query.get(edital_id)
        if not edital:
            return {'erro': 'Edital não encontrado'}
        
        return self.interpreter.classificar_relevancia(
            objeto_licitacao=edital.objeto_completo or edital.objeto_resumo or '',
            segmentos_interesse=segmentos
        )
    
    def resumir_edital(self, edital_id: int) -> dict:
        """Gera resumo executivo de um edital usando Claude AI."""
        if not self.interpreter:
            return {'erro': 'Claude API não configurada'}
        
        edital = Edital.query.get(edital_id)
        if not edital:
            return {'erro': 'Edital não encontrado'}
        
        texto = None
        arquivo = edital.arquivos.filter_by(tipo='edital').first()
        if arquivo and arquivo.texto_extraido:
            texto = arquivo.texto_extraido
        if not texto:
            texto = edital.objeto_completo or edital.objeto_resumo or ''
        if not texto:
            return {'erro': 'Texto do edital nao disponivel'}
        return self.interpreter.resumir_edital(texto)
    
    # =========================================================
    # HELPERS INTERNOS
    # =========================================================
    
    def _criar_edital(self, contratacao: dict) -> Edital:
        """Converte dados do PNCP para modelo Edital."""
        orgao = contratacao.get('orgaoEntidade', {})
        unidade = contratacao.get('unidadeOrgao', {})
        
        return Edital(
            numero_controle_pncp=contratacao.get('numeroControlePNCP'),
            numero_pregao=contratacao.get('numeroCompra'),
            numero_processo=contratacao.get('processo'),
            ano_compra=contratacao.get('anoCompra'),
            sequencial_compra=contratacao.get('sequencialCompra'),
            
            orgao_cnpj=orgao.get('cnpj'),
            orgao_razao_social=orgao.get('razaoSocial'),
            unidade_codigo=unidade.get('codigoUnidade'),
            unidade_nome=unidade.get('nomeUnidade'),
            uf=contratacao.get('uf'),
            municipio=contratacao.get('municipioNome'),
            
            objeto_resumo=contratacao.get('objetoCompra', '')[:500],
            objeto_completo=contratacao.get('objetoCompra'),
            
            modalidade_id=contratacao.get('modalidadeId'),
            modalidade_nome=contratacao.get('modalidadeNome'),
            srp=contratacao.get('srp', False),
            
            data_publicacao=self._parse_data(contratacao.get('dataPublicacaoPncp')),
            data_abertura_proposta=self._parse_data(contratacao.get('dataAberturaProposta')),
            data_encerramento_proposta=self._parse_data(contratacao.get('dataEncerramentoProposta')),
            
            valor_estimado=contratacao.get('valorTotalEstimado'),
            
            plataforma_origem='pncp',
            url_original=f"https://pncp.gov.br/app/editais/{contratacao.get('numeroControlePNCP', '')}",
            link_sistema_origem=contratacao.get('linkSistemaOrigem'),
            
            situacao_pncp=contratacao.get('situacaoCompraNome'),
            informacao_complementar=contratacao.get('informacaoComplementar'),
            status='captado',
        )
    
    def _contratacao_passa_filtros(self, contratacao: dict, filtros: list) -> bool:
        """Verifica se uma contratação passa em pelo menos um filtro."""
        if not filtros:
            return True
        
        objeto = (contratacao.get('objetoCompra') or '').lower()
        uf = contratacao.get('uf', '')
        valor = contratacao.get('valorTotalEstimado')
        
        for filtro in filtros:
            passa = True
            
            # Palavras-chave (pelo menos uma deve estar no objeto)
            if filtro.palavras_chave:
                if not any(kw.lower() in objeto for kw in filtro.palavras_chave):
                    passa = False
            
            # Palavras de exclusão
            if passa and filtro.palavras_exclusao:
                if any(exc.lower() in objeto for exc in filtro.palavras_exclusao):
                    passa = False
            
            # Região
            if passa and filtro.regioes_uf:
                if uf and uf.upper() not in [u.upper() for u in filtro.regioes_uf]:
                    passa = False
            
            # Faixa de valor
            if passa and valor is not None:
                if filtro.valor_minimo and valor < float(filtro.valor_minimo):
                    passa = False
                if filtro.valor_maximo and valor > float(filtro.valor_maximo):
                    passa = False
            
            if passa:
                return True
        
        return False
    
    def _calcular_prioridade(self, contratacao: dict) -> str:
        """Calcula prioridade com base no valor e prazo."""
        valor = contratacao.get('valorTotalEstimado')
        data_certame = contratacao.get('dataEncerramentoProposta')
        
        if valor and valor > 500000:
            return 'alta'
        if data_certame:
            try:
                data = datetime.fromisoformat(data_certame.replace('Z', '+00:00'))
                dias = (data - datetime.now(timezone.utc)).days
                if dias <= 5:
                    return 'alta'
                elif dias <= 10:
                    return 'media'
            except (ValueError, TypeError):
                pass
        return 'media'
    
    def _processar_arquivos(self, edital: Edital, contratacao: dict):
        """Busca e registra arquivos do edital no PNCP."""
        try:
            cnpj = contratacao.get('orgaoEntidade', {}).get('cnpj')
            ano = contratacao.get('anoCompra')
            seq = contratacao.get('sequencialCompra')
            
            if not all([cnpj, ano, seq]):
                return
            
            arquivos = self.pncp.buscar_arquivos_contratacao(cnpj, ano, seq)
            
            if isinstance(arquivos, list):
                for i, arq in enumerate(arquivos):
                    edital_arquivo = EditalArquivo(
                        edital_id=edital.id,
                        tipo='edital' if i == 0 else 'anexo',
                        nome_arquivo=arq.get('nomeArquivo', f'arquivo_{i+1}'),
                        url_original=arq.get('url'),
                        tamanho_bytes=arq.get('tamanho'),
                        mime_type=arq.get('tipoArquivo'),
                    )
                    db.session.add(edital_arquivo)
                    
        except Exception as e:
            logger.warning(f"Erro ao processar arquivos do edital {edital.id}: {e}")
    
    def _carregar_filtros(self, filtros_ids: list = None) -> list:
        """Carrega filtros de prospecção ativos."""
        query = FiltroProspeccao.query.filter_by(ativo=True)
        if filtros_ids:
            query = query.filter(FiltroProspeccao.id.in_(filtros_ids))
        return query.all()
    
    def _baixar_e_extrair_texto(self, url: str) -> str:
        """Baixa PDF de uma URL e extrai texto."""
        try:
            import requests as req
            response = req.get(url, timeout=60)
            response.raise_for_status()
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                f.write(response.content)
                temp_path = f.name
            
            texto, metodo = PDFTextExtractor.extrair_texto_auto(temp_path)
            os.unlink(temp_path)
            
            return texto
        except Exception as e:
            logger.error(f"Erro ao baixar/extrair PDF: {e}")
            return ''
    
    @staticmethod
    def _parse_data(data_str: str) -> Optional[datetime]:
        """Parse de data ISO do PNCP."""
        if not data_str:
            return None
        try:
            return datetime.fromisoformat(data_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
