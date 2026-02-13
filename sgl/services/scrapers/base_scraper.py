"""
SGL - Base Scraper
Classe base para scrapers de plataformas de licitação.
"""
import logging
import time
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class EditalScrapado:
    """Dados padronizados de um edital capturado por scraper."""

    def __init__(self, **kwargs):
        self.numero_processo = kwargs.get('numero_processo', '')
        self.objeto = kwargs.get('objeto', '')
        self.orgao = kwargs.get('orgao', '')
        self.uf = kwargs.get('uf', '')
        self.municipio = kwargs.get('municipio', '')
        self.modalidade = kwargs.get('modalidade', '')
        self.valor_estimado = kwargs.get('valor_estimado')
        self.data_abertura = kwargs.get('data_abertura')
        self.data_publicacao = kwargs.get('data_publicacao')
        self.url_edital = kwargs.get('url_edital', '')
        self.url_plataforma = kwargs.get('url_plataforma', '')
        self.plataforma = kwargs.get('plataforma', '')
        self.status = kwargs.get('status', '')
        self.srp = kwargs.get('srp', False)
        self.numero_pncp = kwargs.get('numero_pncp', '')
        self.dados_extras = kwargs.get('dados_extras', {})

    @property
    def hash_unico(self) -> str:
        """Gera hash único para detecção de duplicatas."""
        chave = f"{self.plataforma}|{self.numero_processo}|{self.orgao}"
        return hashlib.md5(chave.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            'numero_processo': self.numero_processo,
            'objeto': self.objeto,
            'orgao': self.orgao,
            'uf': self.uf,
            'municipio': self.municipio,
            'modalidade': self.modalidade,
            'valor_estimado': self.valor_estimado,
            'data_abertura': self.data_abertura,
            'data_publicacao': self.data_publicacao,
            'url_edital': self.url_edital,
            'url_plataforma': self.url_plataforma,
            'plataforma': self.plataforma,
            'status': self.status,
            'srp': self.srp,
            'numero_pncp': self.numero_pncp,
            'hash_unico': self.hash_unico,
            'dados_extras': self.dados_extras,
        }


class BaseScraper(ABC):
    """
    Classe base para todos os scrapers.
    Fornece: sessão HTTP com retry, rate limiting, logging padronizado.
    """

    PLATAFORMA = 'base'
    BASE_URL = ''

    def __init__(self, timeout=30, max_retries=3, delay_entre_requests=1.0):
        self.timeout = timeout
        self.delay = delay_entre_requests

        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })

        self._last_request_time = 0

    def _rate_limit(self):
        """Respeita delay entre requests."""
        agora = time.time()
        diff = agora - self._last_request_time
        if diff < self.delay:
            time.sleep(self.delay - diff)
        self._last_request_time = time.time()

    def _get(self, url, params=None, **kwargs) -> requests.Response:
        """GET com rate limiting."""
        self._rate_limit()
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 422:
                logger.warning(f"{self.PLATAFORMA}: 422 para {url}")
                return resp
            logger.error(f"{self.PLATAFORMA} HTTP Error: {e}")
            raise
        except Exception as e:
            logger.error(f"{self.PLATAFORMA} Error: {e}")
            raise

    def _post(self, url, data=None, json=None, **kwargs) -> requests.Response:
        """POST com rate limiting."""
        self._rate_limit()
        try:
            resp = self.session.post(url, data=data, json=json, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.error(f"{self.PLATAFORMA} POST Error: {e}")
            raise

    @abstractmethod
    def buscar_editais(
        self,
        termo: Optional[str] = None,
        uf: Optional[str] = None,
        data_inicial: Optional[str] = None,
        data_final: Optional[str] = None,
        pagina: int = 1,
        **kwargs
    ) -> list[EditalScrapado]:
        """Busca editais na plataforma. Deve ser implementado por cada scraper."""
        pass

    def buscar_todos(
        self,
        termo: Optional[str] = None,
        uf: Optional[str] = None,
        data_inicial: Optional[str] = None,
        data_final: Optional[str] = None,
        max_paginas: int = 5,
        **kwargs
    ) -> list[EditalScrapado]:
        """Busca paginada completa."""
        todos = []
        for pagina in range(1, max_paginas + 1):
            try:
                resultados = self.buscar_editais(
                    termo=termo,
                    uf=uf,
                    data_inicial=data_inicial,
                    data_final=data_final,
                    pagina=pagina,
                    **kwargs
                )
                if not resultados:
                    break
                todos.extend(resultados)
                logger.info(f"{self.PLATAFORMA}: Página {pagina} → {len(resultados)} editais")
                if len(resultados) < 20:  # Provavelmente última página
                    break
            except Exception as e:
                logger.error(f"{self.PLATAFORMA}: Erro na página {pagina}: {e}")
                break

        logger.info(f"{self.PLATAFORMA}: Total de {len(todos)} editais encontrados")
        return todos
