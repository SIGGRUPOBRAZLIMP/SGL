"""
SGL - Serviço de Captação de Editais
Combina: API PNCP + Filtros Inteligentes + Claude AI + Storage
"""
import hashlib
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
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
        periodo_dias: Optional[int] = None,
        ufs: Optional[list[str]] = None,
        modalidades: Optional[list[int]] = None,
        filtros_ids: Optional[list[int]] = None
    ) -> dict:
        """
        Executa ciclo completo de captação.
        
        Args:
            data_inicial: Data início YYYYMMDD (opcional)
            data_final: Data fim YYYYMMDD (opcional)
            periodo_dias: Buscar últimos N dias (alternativa a data_inicial/data_final)
            ufs: Lista de UFs para filtrar
            modalidades: Lista de IDs de modalidades
            filtros_ids: IDs de filtros de prospecção a aplicar
        
        Returns:
            dict com estatísticas detalhadas da captação
        """
        stats = {
            'total_encontrados': 0,
            'novos_salvos': 0,
            'duplicados': 0,
            'filtrados': 0,
            'erros': 0,
            'itens_extraidos': 0,
            'detalhes_uf': {},
            'periodo': {},
            'motivos_filtrados': [],
        }
        
        # --- Resolver período de busca ---
        hoje = datetime.now()
        
        if periodo_dias and not data_inicial:
            # Período em dias: busca de (hoje - N dias) até hoje
            inicio = hoje - timedelta(days=periodo_dias)
            data_inicial = formatar_data_pncp(inicio)
            data_final = formatar_data_pncp(hoje)
        else:
            if not data_inicial:
                data_inicial = formatar_data_pncp(hoje)
            if not data_final:
                data_final = formatar_data_pncp(hoje)
        
        stats['periodo'] = {
            'data_inicial': data_inicial,
            'data_final': data_final,
            'periodo_dias': periodo_dias,
        }
        
        if not modalidades:
            # Ler defaults do .env (configurável sem alterar código)
            import os
            env_mod = os.environ.get('PNCP_MODALIDADES_DEFAULT', '4,6,7,8,12')
            modalidades = [int(m.strip()) for m in env_mod.split(',') if m.strip()]
        
        # Carregar filtros de prospecção ativos
        filtros = self._carregar_filtros(filtros_ids)
        
        # Para cada combinação UF + modalidade
        ufs_busca = ufs or [None]  # None = todas as UFs
        
        logger.info(
            f"Captação iniciada | Período: {data_inicial} → {data_final} "
            f"| UFs: {ufs or 'TODAS'} | Modalidades: {modalidades} "
            f"| Filtros ativos: {len(filtros)}"
        )
        
        for uf in ufs_busca:
            uf_stats = {'encontrados': 0, 'novos_salvos': 0, 'duplicados': 0, 'filtrados': 0, 'erros': 0}
            
            for modalidade in modalidades:
                try:
                    contratacoes = self.pncp.buscar_todas_contratacoes(
                        data_inicial=data_inicial,
                        data_final=data_final,
                        modalidade=modalidade,
                        uf=uf,
                        max_paginas=10
                    )
                    
                    uf_stats['encontrados'] += len(contratacoes)
                    stats['total_encontrados'] += len(contratacoes)
                    
                    for contratacao in contratacoes:
                        resultado = self._processar_contratacao(contratacao, filtros, stats)
                        uf_stats[resultado] += 1
                        stats[resultado] += 1
                        
                except Exception as e:
                    logger.error(f"Erro na captação UF={uf} MOD={modalidade}: {e}")
                    stats['erros'] += 1
                    uf_stats['erros'] += 1
            
            uf_label = uf or 'TODAS'
            stats['detalhes_uf'][uf_label] = uf_stats
            
            logger.info(
                f"  UF={uf_label}: {uf_stats['encontrados']} encontrados, "
                f"{uf_stats['novos_salvos']} novos, {uf_stats['duplicados']} duplicados, "
                f"{uf_stats['filtrados']} filtrados, {uf_stats['erros']} erros"
            )
        
        logger.info(
            f"Captação finalizada | "
            f"Total: {stats['total_encontrados']} encontrados, "
            f"{stats['novos_salvos']} novos salvos, "
            f"{stats['duplicados']} duplicados, "
            f"{stats['filtrados']} filtrados, "
            f"{stats['erros']} erros"
        )
        
        return stats
    
    def _processar_contratacao(self, contratacao: dict, filtros: list, stats: dict) -> str:
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
            if filtros:
                passa, motivo = self._contratacao_passa_filtros(contratacao, filtros)
                if not passa:
                    # Logging detalhado do motivo da exclusão
                    orgao = contratacao.get('unidadeOrgao', {}).get('nomeUnidade', 'N/A')
                    objeto = (contratacao.get('objetoCompra') or '')[:60]
                    logger.debug(
                        f"  Filtrado: [{motivo}] {orgao} - {objeto}"
                    )
                    stats['motivos_filtrados'].append(motivo)
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
            
            db.session.commit()
            
            logger.info(
                f"  ✓ Novo edital: {numero_pncp} | "
                f"{contratacao.get('unidadeOrgao', {}).get('ufSigla', '??')}/{contratacao.get('municipioNome', '??')} | "
                f"{edital.objeto_resumo[:80]}"
            )
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
        Pode ser chamado manualmente ou via scheduler.
        
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
                    return {'erro': 'Sem texto disponível para extração'}
                resultado = self.interpreter.extrair_itens(texto_obj)
                itens_salvos = 0
                for item in resultado.get('itens', []):
                    item_db = ItemEditalExtraido(
                        edital_id=edital.id,
                        descricao=item.get('descricao'),
                        quantidade=item.get('quantidade'),
                        unidade=item.get('unidade'),
                        valor_estimado=item.get('valor_estimado'),
                        codigo_catmat=item.get('codigo_catmat'),
                    )
                    db.session.add(item_db)
                    itens_salvos += 1
                db.session.commit()
                resultado['itens_salvos'] = itens_salvos
                return resultado

        texto = arquivo_edital.texto_extraido
        resultado = self.interpreter.extrair_itens(texto)
        
        itens_salvos = 0
        for item in resultado.get('itens', []):
            item_db = ItemEditalExtraido(
                edital_id=edital.id,
                descricao=item.get('descricao'),
                quantidade=item.get('quantidade'),
                unidade=item.get('unidade'),
                valor_estimado=item.get('valor_estimado'),
                codigo_catmat=item.get('codigo_catmat'),
            )
            db.session.add(item_db)
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
            uf=contratacao.get('unidadeOrgao', {}).get('ufSigla') or contratacao.get('uf'),
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
    
    def _contratacao_passa_filtros(self, contratacao: dict, filtros: list) -> tuple:
        """
        Verifica se uma contratação passa em pelo menos um filtro.
        
        Returns:
            tuple (bool, str): (passou, motivo_exclusao)
        """
        if not filtros:
            return True, ''
        
        objeto = (contratacao.get('objetoCompra') or '').lower()
        uf = contratacao.get('unidadeOrgao', {}).get('ufSigla') or contratacao.get('uf', '')
        valor = contratacao.get('valorTotalEstimado')
        
        ultimo_motivo = 'nenhum_filtro_aplicavel'
        
        for filtro in filtros:
            passa = True
            motivo = ''
            
            # Palavras-chave (pelo menos uma deve estar no objeto)
            if filtro.palavras_chave:
                if not any(kw.lower() in objeto for kw in filtro.palavras_chave):
                    passa = False
                    motivo = f'palavras_chave ({filtro.nome})'
            
            # Palavras de exclusão
            if passa and filtro.palavras_exclusao:
                if any(exc.lower() in objeto for exc in filtro.palavras_exclusao):
                    palavra_encontrada = next(exc for exc in filtro.palavras_exclusao if exc.lower() in objeto)
                    passa = False
                    motivo = f'palavra_exclusao: "{palavra_encontrada}" ({filtro.nome})'
            
            # Região
            if passa and filtro.regioes_uf:
                if uf and uf.upper() not in [u.upper() for u in filtro.regioes_uf]:
                    passa = False
                    motivo = f'uf: {uf} não em {filtro.regioes_uf} ({filtro.nome})'
            
            # Faixa de valor
            if passa and valor is not None:
                if filtro.valor_minimo and valor < float(filtro.valor_minimo):
                    passa = False
                    motivo = f'valor: {valor} < mín {filtro.valor_minimo} ({filtro.nome})'
                if filtro.valor_maximo and valor > float(filtro.valor_maximo):
                    passa = False
                    motivo = f'valor: {valor} > máx {filtro.valor_maximo} ({filtro.nome})'
            
            if passa:
                return True, ''
            
            ultimo_motivo = motivo
        
        return False, ultimo_motivo
    
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
