"""
SGL - Scraper Licitar Digital
Captura editais da plataforma Licitar Digital via API REST.
API base: https://manager-api.licitardigital.com.br
Usa FlareSolverr para bypass de Cloudflare em servidores cloud.
"""
import hashlib
import logging
import os
import re
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
    Usa FlareSolverr para bypass de Cloudflare + autenticacao JWT.
    """

    BASE_URL = "https://manager-api.licitardigital.com.br"
    SEARCH_URL = f"{BASE_URL}/auction-notice/doSearchAuctionNotice"
    DETAIL_URL = f"{BASE_URL}/auction-notice/getAuctionNoticeById"

    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password

        # FlareSolverr URL (servico separado no Render)
        self.flaresolverr_url = os.environ.get(
            "FLARESOLVERR_URL", "http://localhost:8191"
        )

        # Session setup
        if HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper()
        else:
            self.session = requests.Session()

        retry = Retry(
            total=3, backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": "https://app2.licitardigital.com.br",
            "Referer": "https://app2.licitardigital.com.br/",
        })

        self.access_token = None
        self._last_request_time = 0
        self._cf_cookies_obtained = False

    # ============================================================
    # FLARESOLVERR - Cloudflare Bypass
    # ============================================================

    def _resolver_cloudflare(self):
        """
        Usa FlareSolverr para resolver challenge Cloudflare.
        Obtem cf_clearance cookie e User-Agent valido.
        """
        if self._cf_cookies_obtained:
            return True

        flaresolverr_endpoint = self.flaresolverr_url.rstrip("/") + "/v1"

        try:
            logger.info("FlareSolverr: resolvendo Cloudflare...")

            payload = {
                "cmd": "request.get",
                "url": "https://manager-api.licitardigital.com.br/",
                "maxTimeout": 60000,
            }

            resp = requests.post(
                flaresolverr_endpoint,
                json=payload,
                timeout=90,
            )

            if resp.status_code != 200:
                logger.error("FlareSolverr HTTP %d: %s", resp.status_code, resp.text[:200])
                return False

            data = resp.json()

            if data.get("status") != "ok":
                logger.error("FlareSolverr erro: %s", data.get("message", "unknown"))
                return False

            solution = data.get("solution", {})
            cookies = solution.get("cookies", [])
            user_agent = solution.get("userAgent", "")

            # Aplicar cookies na sessao
            cf_found = False
            for cookie in cookies:
                name = cookie.get("name", "")
                value = cookie.get("value", "")
                domain = cookie.get("domain", "")

                self.session.cookies.set(
                    name, value,
                    domain=domain or ".licitardigital.com.br"
                )

                if name == "cf_clearance":
                    cf_found = True
                    logger.info("FlareSolverr: cf_clearance obtido")

            # Aplicar User-Agent do browser real
            if user_agent:
                self.session.headers["User-Agent"] = user_agent

            self._cf_cookies_obtained = True

            if cf_found:
                logger.info("FlareSolverr: Cloudflare resolvido com sucesso!")
            else:
                logger.warning("FlareSolverr: sem cf_clearance, tentando continuar...")

            return True

        except requests.exceptions.ConnectionError:
            logger.warning("FlareSolverr indisponivel em %s", self.flaresolverr_url)
            return False
        except Exception as e:
            logger.error("FlareSolverr erro: %s", e)
            return False

    # ============================================================
    # API Request com retry via FlareSolverr
    # ============================================================

    def _api_post(self, url, json_data, timeout=60):
        """POST request com fallback para FlareSolverr se Cloudflare bloquear."""
        self._rate_limit()

        resp = self.session.post(url, json=json_data, timeout=timeout)

        # Se Cloudflare bloqueou (403), tentar resolver e repetir
        if resp.status_code == 403 and not self._cf_cookies_obtained:
            logger.info("Cloudflare 403 detectado, tentando FlareSolverr...")
            if self._resolver_cloudflare():
                self._rate_limit(1.0)
                resp = self.session.post(url, json=json_data, timeout=timeout)

        return resp

    # ============================================================
    # RATE LIMITING
    # ============================================================

    def _rate_limit(self, delay=0.5):
        """Respeita delay entre requisicoes."""
        agora = time.time()
        diff = agora - self._last_request_time
        if diff < delay:
            time.sleep(delay - diff)
        self._last_request_time = time.time()

    # ============================================================
    # AUTENTICACAO
    # ============================================================

    def autenticar(self):
        """Autentica no Licitar Digital. Resolve Cloudflare primeiro."""
        # Tentar resolver Cloudflare antes do login
        self._resolver_cloudflare()

        endpoints_login = [
            self.BASE_URL + "/auth/login",
            self.BASE_URL + "/auth",
        ]

        payloads = [
            {"cpf": self.username, "password": self.password},
            {"login": self.username, "password": self.password},
            {"username": self.username, "password": self.password},
        ]

        for endpoint in endpoints_login:
            for payload in payloads:
                try:
                    self._rate_limit(0.3)
                    resp = self._api_post(endpoint, payload, timeout=30)

                    if resp.status_code in [200, 201]:
                        data = resp.json()
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
                            self.session.headers["Authorization"] = "Bearer " + token
                            logger.info("Licitar Digital: autenticado (%s...)", token[:30])
                            return True

                except Exception as e:
                    logger.debug("Erro em %s: %s", endpoint, e)
                    continue

        logger.error("Licitar Digital: falha na autenticacao")
        return False

    def _set_token_manual(self, token):
        """Define token manualmente (obtido via browser)."""
        self.access_token = token
        self.session.headers["Authorization"] = "Bearer " + token
        logger.info("Licitar Digital: token manual configurado (%s...)", token[:30])

    # ============================================================
    # BUSCA DE EDITAIS
    # ============================================================

    def buscar_editais(self, offset=0, limit=20, short_filter="all",
                       start_date=0, start_date_publication=0):
        """Busca editais na plataforma Licitar Digital."""
        if not self.access_token:
            raise RuntimeError("Nao autenticado.")

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
            resp = self._api_post(self.SEARCH_URL, payload, timeout=60)

            if resp.status_code in [200, 201]:
                data = resp.json()
                if data.get("status") == "success":
                    editais = data.get("data", [])
                    meta = data.get("meta", {})
                    logger.info(
                        "Licitar Digital: %d editais (offset=%d, total=%s)",
                        len(editais), offset, meta.get("count", "?")
                    )
                    return data
                else:
                    logger.warning("Licitar Digital busca falhou: %s", data)
                    return {"data": [], "meta": {"count": 0}}
            else:
                logger.error("Licitar Digital HTTP %d: %s", resp.status_code, resp.text[:200])
                return {"data": [], "meta": {"count": 0}}

        except Exception as e:
            logger.error("Erro na busca Licitar Digital: %s", e)
            return {"data": [], "meta": {"count": 0}}

    def buscar_detalhe(self, auction_id):
        """Busca detalhe de um edital especifico."""
        if not self.access_token:
            raise RuntimeError("Nao autenticado.")

        payload = {"auctionId": auction_id, "step": "afterPublished"}

        try:
            resp = self._api_post(self.DETAIL_URL, payload, timeout=30)
            if resp.status_code in [200, 201]:
                data = resp.json()
                if data.get("status") == "success":
                    return data.get("data", {})
            return {}
        except Exception as e:
            logger.error("Erro detalhe edital %s: %s", auction_id, e)
            return {}

    def buscar_todos_editais(self, dias_recentes=30, short_filter="all"):
        """Busca todos os editais com paginacao automatica."""
        todos = []
        offset = 0
        limit = 20
        total = None
        data_limite = datetime.now(timezone.utc) - timedelta(days=dias_recentes)

        while True:
            resultado = self.buscar_editais(offset=offset, limit=limit, short_filter=short_filter)
            editais = resultado.get("data", [])
            meta = resultado.get("meta", {})

            if total is None:
                total = meta.get("count", 0)
                logger.info("Licitar Digital: %d editais totais disponiveis", total)

            if not editais:
                break

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
            if offset >= total:
                break
            if offset >= 200:
                logger.warning("Licitar Digital: limite de 200 editais atingido")
                break

        logger.info("Licitar Digital: %d editais recentes (ultimos %d dias)", len(todos), dias_recentes)
        return todos

    # ============================================================
    # CONVERSAO PARA FORMATO SGL
    # ============================================================

    @staticmethod
    def converter_para_sgl(edital):
        """Converte um edital do Licitar Digital para o formato SGL."""
        auction_id = edital.get("id", "")
        org_name = edital.get("organizationName", "")
        process_number = edital.get("auctionNumber", "")

        hash_str = "licitardigital:" + str(auction_id)
        hash_scraper = hashlib.md5(hash_str.encode()).hexdigest()

        # Extrair UF
        uf = ""
        if org_name:
            match = re.search(r'/([A-Z]{2})(?:\s|$|\.)', org_name)
            if match:
                uf = match.group(1)
            if not uf:
                desc = edital.get("simpleDescription", "")
                match = re.search(r'/([A-Z]{2})(?:\s|$|\.|,)', desc)
                if match:
                    uf = match.group(1)

        # Municipio
        municipio = ""
        if org_name:
            match = re.search(
                r'(?:Prefeitura|Câmara|Autarquia)\s+(?:Municipal)\s+de\s+(.+?)(?:\s*[-/]\s*\w{2})?$',
                org_name, re.IGNORECASE,
            )
            if match:
                municipio = match.group(1).strip()
            if not municipio:
                match2 = re.search(r'de\s+([\w\s]+)/[A-Z]{2}', org_name)
                if match2:
                    municipio = match2.group(1).strip()

        # Modalidade
        auction_type = edital.get("auctionType", "")
        tipo_map = {
            "E": "Pregão Eletrônico",
            "D": "Dispensa de Licitação",
            "P": "Pregão Presencial",
        }
        modalidade = tipo_map.get(auction_type, "Tipo " + str(auction_type))

        # Status
        stage_id = edital.get("biddingStageId", 0)
        stage_map = {
            8: "Publicado", 9: "Em andamento", 10: "Encerrado",
            11: "Homologado", 12: "Cancelado",
        }
        status_edital = stage_map.get(stage_id, "Stage " + str(stage_id))

        # URL
        platform = edital.get("platform", "licitardigital")
        if platform == "ammlicita":
            url_original = "https://ammlicita.org.br/processo/" + str(auction_id)
        else:
            url_original = "https://app2.licitardigital.com.br/processo/" + str(auction_id)

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
            "srp": "registro de preco" in (edital.get("simpleDescription") or "").lower(),
            "data_publicacao": edital.get("dateTimeInsert"),
            "data_abertura_proposta": edital.get("auctionStartDate"),
            "data_encerramento_proposta": edital.get("startDateTimeDispute"),
            "plataforma_origem": "licitardigital",
            "url_original": url_original,
            "link_sistema_origem": url_original,
            "situacao_pncp": status_edital,
            "status": "captado",
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
# FUNCAO STANDALONE PARA CAPTACAO
# ============================================================

def captar_editais_licitardigital(username, password, dias_recentes=7, token_manual=None):
    """Funcao standalone para captacao de editais do Licitar Digital."""
    resultado = {
        "sucesso": False,
        "editais": [],
        "stats": {"total_encontrados": 0, "convertidos": 0},
        "erro": None,
    }

    try:
        scraper = LicitarDigitalScraper(username, password)

        autenticado = False
        if token_manual:
            scraper._set_token_manual(token_manual)
            autenticado = True
        if not autenticado:
            autenticado = scraper.autenticar()
        if not autenticado and token_manual:
            logger.info("Login automatico falhou, usando token manual")
            scraper._set_token_manual(token_manual)
            autenticado = True

        if not autenticado:
            resultado["erro"] = "Falha na autenticacao Licitar Digital"
            return resultado

        editais = scraper.buscar_todos_editais(
            dias_recentes=dias_recentes, short_filter="all",
        )

        resultado["stats"]["total_encontrados"] = len(editais)

        editais_sgl = []
        for edital in editais:
            try:
                sgl = LicitarDigitalScraper.converter_para_sgl(edital)
                editais_sgl.append(sgl)
            except Exception as e:
                logger.warning("Erro ao converter edital %s: %s", edital.get("id"), e)

        resultado["editais"] = editais_sgl
        resultado["stats"]["convertidos"] = len(editais_sgl)
        resultado["sucesso"] = True

        logger.info(
            "Licitar Digital captacao: %d encontrados, %d convertidos",
            len(editais), len(editais_sgl)
        )

    except Exception as e:
        resultado["erro"] = str(e)
        logger.error("Erro na captacao Licitar Digital: %s", e, exc_info=True)

    return resultado
