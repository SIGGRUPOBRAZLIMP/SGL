"""
SGL - Scraper Licitar Digital
Captura editais da plataforma Licitar Digital via API REST.
API base: https://manager-api.licitardigital.com.br
"""
import hashlib
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import requests
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class LicitarDigitalScraper:
    """
    Scraper para a plataforma Licitar Digital.
    Usa autenticação JWT via login com CPF/senha.
    """

    BASE_URL = "https://manager-api.licitardigital.com.br"
    AUTH_URL = f"{BASE_URL}/auth"
    SEARCH_URL = f"{BASE_URL}/auction-notice/doSearchAuctionNotice"
    DETAIL_URL = f"{BASE_URL}/auction-notice/getAuctionNoticeById"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = cloudscraper.create_scraper() if HAS_CLOUDSCRAPER else requests.Session()

        # Retry strategy
        retry = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": "https://app2.licitardigital.com.br",
            "Referer": "https://app2.licitardigital.com.br/",
        })

        self.access_token = None
        self._last_request_time = 0

    # ============================================================
    # RATE LIMITING
    # ============================================================

    def _rate_limit(self, delay: float = 0.5):
        """Respeita delay entre requisições."""
        agora = time.time()
        diff = agora - self._last_request_time
        if diff < delay:
            time.sleep(delay - diff)
        self._last_request_time = time.time()

    # ============================================================
    # AUTENTICAÇÃO
    # ============================================================

    def autenticar(self) -> bool:
        """
        Autentica no Licitar Digital via CPF + senha.
        Tenta múltiplos endpoints de login.
        """
        endpoints_login = [
            f"{self.BASE_URL}/auth/login",
            f"{self.BASE_URL}/auth",
            f"{self.BASE_URL}/user/login",
            f"{self.BASE_URL}/authentication/login",
            f"{self.BASE_URL}/login",
        ]

        # Payloads possíveis
        payloads = [
            {"cpf": self.username, "password": self.password},
            {"login": self.username, "password": self.password},
            {"username": self.username, "password": self.password},
            {"cpf": self.username, "senha": self.password},
            {"email": self.username, "password": self.password},
            {"document": self.username, "password": self.password},
        ]

        for endpoint in endpoints_login:
            for payload in payloads:
                try:
                    self._rate_limit(0.3)
                    logger.debug(f"Tentando login: {endpoint} com keys={list(payload.keys())}")

                    resp = self.session.post(
                        endpoint,
                        json=payload,
                        timeout=30,
                    )

                    if resp.status_code in [200, 201]:
                        data = resp.json()

                        # Extrair token de diversas estruturas possíveis
                        token = (
                            data.get("token")
                            or data.get("access_token")
                            or data.get("accessToken")
                            or (data.get("data", {}) or {}).get("token")
                            or (data.get("data", {}) or {}).get("access_token")
                            or (data.get("data", {}) or {}).get("accessToken")
                        )

                        if token:
                            self.access_token = token
                            self.session.headers["Authorization"] = f"Bearer {token}"
                            logger.info(
                                f"Licitar Digital: autenticado via {endpoint} "
                                f"(token: {token[:30]}...)"
                            )
                            return True

                        # Se retornou 200/201 mas sem token no JSON, logar resposta
                        logger.debug(f"Login 200/201 mas sem token: {list(data.keys())}")

                except requests.exceptions.HTTPError:
                    continue
                except Exception as e:
                    logger.debug(f"Erro em {endpoint}: {e}")
                    continue

        logger.error("Licitar Digital: falha na autenticação em todos endpoints")
        return False

    def _set_token_manual(self, token: str):
        """Define token manualmente (obtido via browser)."""
        self.access_token = token
        self.session.headers["Authorization"] = f"Bearer {token}"
        logger.info(f"Licitar Digital: token manual configurado ({token[:30]}...)")

    # ============================================================
    # BUSCA DE EDITAIS
    # ============================================================

    def buscar_editais(
        self,
        offset: int = 0,
        limit: int = 20,
        short_filter: str = "all",
        start_date: int = 0,
        start_date_publication: int = 0,
    ) -> dict:
        """
        Busca editais na plataforma Licitar Digital.

        Args:
            offset: Início da paginação
            limit: Itens por página (padrão 20)
            short_filter: "all", "proposal", "suggestion", "favorite"
            start_date: Timestamp para filtro de data início
            start_date_publication: Timestamp para filtro de data publicação

        Returns:
            dict com {data: [...], meta: {count, limit, offset}}
        """
        if not self.access_token:
            raise RuntimeError("Não autenticado. Chame autenticar() primeiro.")

        self._rate_limit()

        payload = {
            "filter": {
                "supliesProviders": [],
                "shortFilter": short_filter,
                "startDate": start_date,
                "startDatePublication": start_date_publication,
                "endDate": 0,
                "endDatePublication": 0,
                "organizationUnitId": None,
                "searchField": "",
                "biddingStageId": None,
                "ruleId": None,
                "legalSupportId": None,
                "isCanceled": False,
            },
            "offset": offset,
        }

        try:
            resp = self.session.post(
                self.SEARCH_URL,
                json=payload,
                timeout=60,
            )

            if resp.status_code in [200, 201]:
                data = resp.json()
                if data.get("status") == "success":
                    editais = data.get("data", [])
                    meta = data.get("meta", {})
                    logger.info(
                        f"Licitar Digital: {len(editais)} editais "
                        f"(offset={offset}, total={meta.get('count', '?')})"
                    )
                    return data
                else:
                    logger.warning(f"Licitar Digital busca falhou: {data}")
                    return {"data": [], "meta": {"count": 0}}
            else:
                logger.error(f"Licitar Digital busca HTTP {resp.status_code}: {resp.text[:200]}")
                return {"data": [], "meta": {"count": 0}}

        except Exception as e:
            logger.error(f"Erro na busca Licitar Digital: {e}")
            return {"data": [], "meta": {"count": 0}}

    def buscar_detalhe(self, auction_id: int) -> dict:
        """Busca detalhe de um edital específico."""
        if not self.access_token:
            raise RuntimeError("Não autenticado.")

        self._rate_limit()

        payload = {
            "auctionId": auction_id,
            "step": "afterPublished",
        }

        try:
            resp = self.session.post(
                self.DETAIL_URL,
                json=payload,
                timeout=30,
            )

            if resp.status_code in [200, 201]:
                data = resp.json()
                if data.get("status") == "success":
                    return data.get("data", {})
            
            logger.warning(f"Detalhe edital {auction_id}: HTTP {resp.status_code}")
            return {}

        except Exception as e:
            logger.error(f"Erro detalhe edital {auction_id}: {e}")
            return {}

    def buscar_todos_editais(self, dias_recentes: int = 30, short_filter: str = "all") -> list:
        """
        Busca todos os editais com paginação automática.
        Filtra apenas recentes (últimos N dias).

        Args:
            dias_recentes: Filtrar editais dos últimos N dias
            short_filter: "all", "proposal", "suggestion"

        Returns:
            Lista de editais
        """
        todos = []
        offset = 0
        limit = 20
        total = None
        data_limite = datetime.now(timezone.utc) - timedelta(days=dias_recentes)

        while True:
            resultado = self.buscar_editais(
                offset=offset,
                limit=limit,
                short_filter=short_filter,
            )

            editais = resultado.get("data", [])
            meta = resultado.get("meta", {})

            if total is None:
                total = meta.get("count", 0)
                logger.info(f"Licitar Digital: {total} editais totais disponíveis")

            if not editais:
                break

            # Filtrar por data
            for edital in editais:
                dt_insert = edital.get("dateTimeInsert", "")
                if dt_insert:
                    try:
                        dt = datetime.fromisoformat(dt_insert.replace("Z", "+00:00"))
                        if dt >= data_limite:
                            todos.append(edital)
                    except (ValueError, TypeError):
                        todos.append(edital)
                else:
                    todos.append(edital)

            offset += limit

            # Parar se já buscou tudo ou se editais são antigos demais
            if offset >= total:
                break

            # Safety: máximo 10 páginas
            if offset >= 200:
                logger.warning("Licitar Digital: limite de 200 editais atingido")
                break

        logger.info(f"Licitar Digital: {len(todos)} editais recentes (últimos {dias_recentes} dias)")
        return todos

    # ============================================================
    # CONVERSÃO PARA FORMATO SGL
    # ============================================================

    @staticmethod
    def converter_para_sgl(edital: dict) -> dict:
        """
        Converte um edital do Licitar Digital para o formato SGL.
        """
        auction_id = edital.get("id", "")
        org_name = edital.get("organizationName", "")
        process_number = edital.get("auctionNumber", "")

        # Hash único para deduplicação
        hash_str = f"licitardigital:{auction_id}"
        hash_scraper = hashlib.md5(hash_str.encode()).hexdigest()

        # Extrair UF do nome da organização (ex: "...de Minduri/MG")
        uf = ""
        if org_name:
            # Tenta extrair UF do final: "...de CIDADE/UF"
            import re
            match = re.search(r'/([A-Z]{2})(?:\s|$|\.)', org_name)
            if match:
                uf = match.group(1)
            # Fallback: extrair da descrição
            if not uf:
                desc = edital.get("simpleDescription", "")
                match = re.search(r'/([A-Z]{2})(?:\s|$|\.|,)', desc)
                if match:
                    uf = match.group(1)

        # Município: extrair do nome da organização
        municipio = ""
        if org_name:
            # Padrão: "Prefeitura Municipal de CIDADE"
            match = re.search(
                r'(?:Prefeitura|Câmara|Autarquia)\s+(?:Municipal|Municípal)\s+de\s+(.+?)(?:\s*-\s*\w{2})?$',
                org_name,
                re.IGNORECASE,
            )
            if match:
                municipio = match.group(1).strip()

        # Mapear tipo de edital
        auction_type = edital.get("auctionType", "")
        tipo_map = {"E": "Pregão Eletrônico", "D": "Dispensa de Licitação", "P": "Pregão Presencial"}
        modalidade = tipo_map.get(auction_type, f"Tipo {auction_type}")

        # Status
        stage_id = edital.get("biddingStageId", 0)
        stage_map = {
            8: "Publicado",
            9: "Em andamento",
            10: "Encerrado",
            11: "Homologado",
            12: "Cancelado",
        }
        status_edital = stage_map.get(stage_id, f"Stage {stage_id}")

        # URL do edital
        platform = edital.get("platform", "licitardigital")
        if platform == "ammlicita":
            url_original = f"https://ammlicita.org.br/processo/{auction_id}"
        else:
            url_original = f"https://app2.licitardigital.com.br/processo/{auction_id}"

        return {
            "hash_scraper": hash_scraper,
            "numero_pregao": process_number,
            "numero_processo": edital.get("accreditationNumber", process_number),

            "orgao_cnpj": None,
            "orgao_razao_social": org_name,
            "unidade_nome": edital.get("organizationUnitName"),
            "uf": uf,
            "municipio": municipio,

            "objeto_resumo": (edital.get("simpleDescription") or "")[:500],
            "objeto_completo": edital.get("simpleDescription"),

            "modalidade_nome": modalidade,
            "srp": "registro de preço" in (edital.get("simpleDescription") or "").lower(),

            "data_publicacao": edital.get("dateTimeInsert"),
            "data_abertura_proposta": edital.get("auctionStartDate"),
            "data_encerramento_proposta": edital.get("startDateTimeDispute"),

            "plataforma_origem": "licitardigital",
            "url_original": url_original,
            "link_sistema_origem": url_original,

            "situacao_pncp": status_edital,
            "status": "captado",

            # Dados extras para referência
            "dados_extras": {
                "auction_id": auction_id,
                "platform": platform,
                "bidding_stage_id": stage_id,
                "legal_support_id": edital.get("legalSupportId"),
                "method_dispute": edital.get("methodDispute"),
                "organization_id": edital.get("organizationId"),
            },
        }


# ============================================================
# FUNÇÃO STANDALONE PARA CAPTAÇÃO
# ============================================================

def captar_editais_licitardigital(
    username: str,
    password: str,
    dias_recentes: int = 7,
    token_manual: str = None,
) -> dict:
    """
    Função standalone para captação de editais do Licitar Digital.

    Args:
        username: CPF para login
        password: Senha
        dias_recentes: Buscar últimos N dias
        token_manual: Token JWT manual (se login automático falhar)

    Returns:
        dict com {sucesso, editais, stats, erro}
    """
    resultado = {
        "sucesso": False,
        "editais": [],
        "stats": {"total_encontrados": 0, "convertidos": 0},
        "erro": None,
    }

    try:
        scraper = LicitarDigitalScraper(username, password)

        # Tentar login automático
        autenticado = False
        if token_manual:
            scraper._set_token_manual(token_manual)
            autenticado = True
        if not autenticado:
            autenticado = scraper.autenticar()
            logger.info("Login automático falhou, usando token manual")
            scraper._set_token_manual(token_manual)
            autenticado = True

        if not autenticado:
            resultado["erro"] = "Falha na autenticação Licitar Digital"
            return resultado

        # Buscar editais
        editais = scraper.buscar_todos_editais(
            dias_recentes=dias_recentes,
            short_filter="all",
        )

        resultado["stats"]["total_encontrados"] = len(editais)

        # Converter para formato SGL
        editais_sgl = []
        for edital in editais:
            try:
                sgl = LicitarDigitalScraper.converter_para_sgl(edital)
                editais_sgl.append(sgl)
            except Exception as e:
                logger.warning(f"Erro ao converter edital {edital.get('id')}: {e}")

        resultado["editais"] = editais_sgl
        resultado["stats"]["convertidos"] = len(editais_sgl)
        resultado["sucesso"] = True

        logger.info(
            f"Licitar Digital captação: {len(editais)} encontrados, "
            f"{len(editais_sgl)} convertidos"
        )

    except Exception as e:
        resultado["erro"] = str(e)
        logger.error(f"Erro na captação Licitar Digital: {e}", exc_info=True)

    return resultado
