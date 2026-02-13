"""
SGL - Cliente da API do PNCP
Portal Nacional de Contratações Públicas
Documentação: https://pncp.gov.br/api/consulta/swagger-ui/index.html
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class PNCPClient:
    """
    Cliente para a API de consulta do PNCP.
    API pública, sem necessidade de autenticação.
    """
    
    BASE_URL = 'https://pncp.gov.br/api/consulta/v1'
    
    # Códigos de modalidade
    MODALIDADES = {
        1: 'Leilão - Eletrônico',
        2: 'Diálogo Competitivo',
        3: 'Concurso',
        4: 'Concorrência - Eletrônica',
        5: 'Concorrência - Presencial',
        6: 'Pregão - Presencial',
        7: 'Dispensa de Licitação',
        8: 'Pregão - Eletrônico',
        9: 'Inexigibilidade',
        10: 'Manifestação de Interesse',
        11: 'Pré-qualificação',
        12: 'Credenciamento',
        13: 'Leilão - Presencial',
    }
    
    def __init__(self, timeout=30, max_retries=3, page_size=50):
        self.timeout = timeout
        self.page_size = page_size
        
        # Configurar sessão com retry automático
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'SGL/1.0 (Sistema de Gestão de Licitações)'
        })
    
    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Faz uma requisição GET à API do PNCP"""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 422:
                logger.warning(f"PNCP API 422 (sem dados): {params}")
                return []
            logger.error(f"PNCP API HTTP Error: {e} | URL: {url} | Params: {params}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"PNCP API Connection Error: {e}")
            raise
        except requests.exceptions.Timeout:
            logger.error(f"PNCP API Timeout: {url}")
            raise
        except Exception as e:
            logger.error(f"PNCP API Error: {e}")
            raise
    
    # =========================================================
    # CONTRATAÇÕES (Editais/Licitações)
    # =========================================================
    
    def buscar_contratacoes_por_data(
        self,
        data_inicial: str,
        data_final: str,
        modalidade: Optional[int] = None,
        uf: Optional[str] = None,
        pagina: int = 1,
        tamanho_pagina: Optional[int] = None
    ) -> dict:
        """
        Busca contratações publicadas em um período.
        
        Args:
            data_inicial: Data início no formato YYYYMMDD
            data_final: Data fim no formato YYYYMMDD
            modalidade: Código da modalidade (8=Pregão Eletrônico)
            uf: Sigla do estado (SP, RJ, MG, etc.)
            pagina: Número da página (começa em 1)
            tamanho_pagina: Quantidade por página (max 500)
        
        Returns:
            dict com lista de contratações e metadados de paginação
        """
        params = {
            'dataInicial': data_inicial,
            'dataFinal': data_final,
            'pagina': pagina,
            'tamanhoPagina': tamanho_pagina or self.page_size,
        }
        if modalidade:
            params['codigoModalidadeContratacao'] = modalidade
        if uf:
            params['uf'] = uf.upper()
        
        return self._get('/contratacoes/publicacao', params)
    
    def buscar_contratacoes_propostas_abertas(
        self,
        data_inicial: str,
        data_final: str,
        modalidade: Optional[int] = None,
        uf: Optional[str] = None,
        pagina: int = 1
    ) -> dict:
        """
        Busca contratações com período de recebimento de propostas em aberto.
        Ideal para encontrar licitações que ainda aceitam propostas.
        """
        params = {
            'dataInicial': data_inicial,
            'dataFinal': data_final,
            'pagina': pagina,
            'tamanhoPagina': self.page_size,
        }
        if modalidade:
            params['codigoModalidadeContratacao'] = modalidade
        if uf:
            params['uf'] = uf.upper()
        
        return self._get('/contratacoes/proposta', params)
    
    def buscar_contratacao_detalhes(
        self, 
        cnpj: str, 
        ano: int, 
        sequencial: int
    ) -> dict:
        """
        Busca detalhes de uma contratação específica.
        
        Args:
            cnpj: CNPJ do órgão (apenas números)
            ano: Ano da compra
            sequencial: Sequencial da compra
        """
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        return self._get(f'/orgaos/{cnpj_limpo}/compras/{ano}/{sequencial}')
    
    # =========================================================
    # ITENS DE CONTRATAÇÃO
    # =========================================================
    
    def buscar_itens_contratacao(
        self, 
        cnpj: str, 
        ano: int, 
        sequencial: int
    ) -> list:
        """
        Busca todos os itens de uma contratação.
        Retorna lista com descrição, quantidade, preço, etc.
        """
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        return self._get(f'/orgaos/{cnpj_limpo}/compras/{ano}/{sequencial}/itens')
    
    # =========================================================
    # DOCUMENTOS / ARQUIVOS
    # =========================================================
    
    def buscar_arquivos_contratacao(
        self, 
        cnpj: str, 
        ano: int, 
        sequencial: int
    ) -> list:
        """
        Busca arquivos/documentos de uma contratação (editais, anexos, etc.)
        Retorna URLs para download dos arquivos.
        """
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        return self._get(f'/orgaos/{cnpj_limpo}/compras/{ano}/{sequencial}/arquivos')
    
    def baixar_arquivo(self, cnpj: str, ano: int, sequencial: int, seq_arquivo: int) -> bytes:
        """
        Baixa um arquivo específico de uma contratação.
        Retorna os bytes do arquivo (geralmente PDF).
        """
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        url = f"{self.BASE_URL}/orgaos/{cnpj_limpo}/compras/{ano}/{sequencial}/arquivos/{seq_arquivo}"
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        return response.content
    
    # =========================================================
    # ATAS DE REGISTRO DE PREÇO
    # =========================================================
    
    def buscar_atas_por_data(
        self,
        data_inicial: str,
        data_final: str,
        pagina: int = 1
    ) -> dict:
        """Busca atas de registro de preço publicadas no período."""
        params = {
            'dataInicial': data_inicial,
            'dataFinal': data_final,
            'pagina': pagina,
            'tamanhoPagina': self.page_size,
        }
        return self._get('/atas', params)
    
    # =========================================================
    # CONTRATOS
    # =========================================================
    
    def buscar_contratos_por_data(
        self,
        data_inicial: str,
        data_final: str,
        pagina: int = 1
    ) -> dict:
        """Busca contratos publicados no período."""
        params = {
            'dataInicial': data_inicial,
            'dataFinal': data_final,
            'pagina': pagina,
            'tamanhoPagina': self.page_size,
        }
        return self._get('/contratos', params)
    
    # =========================================================
    # PCA — Plano de Contratações Anual
    # =========================================================
    
    def buscar_pca(
        self,
        ano: int,
        codigo_classificacao: int = None,
        pagina: int = 1
    ) -> dict:
        """
        Busca Planos de Contratações Anuais.
        Útil para antecipar licitações futuras!
        """
        params = {
            'anoPca': ano,
            'pagina': pagina,
        }
        if codigo_classificacao:
            params['codigoClassificacaoSuperior'] = codigo_classificacao
        return self._get('/pca/', params)
    
    # =========================================================
    # MÉTODOS DE CONVENIÊNCIA — BUSCA PAGINADA COMPLETA
    # =========================================================
    
    def buscar_todas_contratacoes(
        self,
        data_inicial: str,
        data_final: str,
        modalidade: Optional[int] = None,
        uf: Optional[str] = None,
        max_paginas: int = 20,
        delay_entre_paginas: float = 0.5
    ) -> list:
        """
        Busca TODAS as contratações de um período, percorrendo todas as páginas.
        
        Args:
            max_paginas: Limite de segurança para não fazer muitas requisições
            delay_entre_paginas: Delay em segundos entre páginas (rate limiting)
        
        Returns:
            Lista com todas as contratações encontradas
        """
        todas = []
        pagina = 1
        
        while pagina <= max_paginas:
            logger.info(f"PNCP: Buscando página {pagina} | {data_inicial} a {data_final} | UF={uf}")
            
            resultado = self.buscar_contratacoes_por_data(
                data_inicial=data_inicial,
                data_final=data_final,
                modalidade=modalidade,
                uf=uf,
                pagina=pagina
            )
            
            # A API retorna lista direta ou dict com dados
            if isinstance(resultado, list):
                if not resultado:
                    break
                todas.extend(resultado)
                if len(resultado) < self.page_size:
                    break  # Última página
            elif isinstance(resultado, dict):
                dados = resultado.get('data', resultado.get('contratacoes', []))
                if not dados:
                    break
                todas.extend(dados)
                
                # Verificar se há mais páginas
                total_paginas = resultado.get('totalPaginas', 1)
                if pagina >= total_paginas:
                    break
            else:
                break
            
            pagina += 1
            if delay_entre_paginas > 0:
                time.sleep(delay_entre_paginas)
        
        logger.info(f"PNCP: Total de {len(todas)} contratações encontradas")
        return todas
    
    def buscar_contratacoes_hoje(
        self,
        modalidade: int = 8,
        uf: Optional[str] = None
    ) -> list:
        """Atalho para buscar contratações publicadas hoje."""
        hoje = datetime.now().strftime('%Y%m%d')
        return self.buscar_todas_contratacoes(
            data_inicial=hoje,
            data_final=hoje,
            modalidade=modalidade,
            uf=uf
        )
    
    def buscar_contratacoes_ultimas_horas(
        self,
        horas: int = 24,
        modalidade: int = 8,
        uf: Optional[str] = None
    ) -> list:
        """Busca contratações publicadas nas últimas N horas."""
        agora = datetime.now()
        inicio = (agora - timedelta(hours=horas)).strftime('%Y%m%d')
        fim = agora.strftime('%Y%m%d')
        return self.buscar_todas_contratacoes(
            data_inicial=inicio,
            data_final=fim,
            modalidade=modalidade,
            uf=uf
        )


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def formatar_data_pncp(data: datetime) -> str:
    """Converte datetime para formato YYYYMMDD do PNCP"""
    return data.strftime('%Y%m%d')


def extrair_cnpj_ano_sequencial(numero_controle_pncp: str) -> tuple:
    """
    Extrai CNPJ, ano e sequencial do número de controle PNCP.
    Formato: CNPJ-ESFERA-SEQUENCIAL/ANO
    Ex: '12345678000199-1-000001/2025' → ('12345678000199', 2025, 1)
    """
    try:
        partes = numero_controle_pncp.split('-')
        cnpj = partes[0]
        seq_ano = partes[2]  # '000001/2025'
        sequencial, ano = seq_ano.split('/')
        return cnpj, int(ano), int(sequencial)
    except (IndexError, ValueError) as e:
        logger.error(f"Erro ao extrair dados do número PNCP: {numero_controle_pncp} | {e}")
        return None, None, None
