"""
SGL - Cliente API Partner Licitar Digital (Oficial)
====================================================
Usa a API Partner oficial documentada em:
  https://licitarpartner.docs.apiary.io/

Autenticação: Basic Auth com clientId:clientSecret (Base64)
Rate limit: 60 req/min (padrão)
Paginação: limit/offset (máx 100 por página)

Variáveis de ambiente:
  LICITAR_PARTNER_CLIENT_ID     - clientId fornecido pela Licitar Digital
  LICITAR_PARTNER_CLIENT_SECRET - clientSecret fornecido pela Licitar Digital
  LICITAR_PARTNER_BASE_URL      - URL base da API (padrão: informado no onboarding)
  LICITAR_PARTNER_ENV           - "production" ou "homologation" (padrão: production)

IMPORTANTE: clientId/clientSecret são DIFERENTES entre homologação e produção.
"""

import base64
import hashlib
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)


class LicitarPartnerClient:
    """Cliente para API Partner oficial da Licitar Digital."""

    # URL base — será informada no onboarding. Configurável via env var.
    DEFAULT_BASE_URL = "https://api.licitardigital.com.br"

    # Mapeamento de modalidades (API Partner → SGL)
    MODALIDADES = {
        "E": "Pregão Eletrônico",
        "C": "Credenciamento",
        "D": "Dispensa Eletrônica",
        "R": "Concorrência Eletrônica",
        "L": "Leilão Eletrônico",
    }

    # Mapeamento de métodos de disputa
    METODOS_DISPUTA = {
        "open": "Aberto",
        "openClose": "Aberto-Fechado",
    }

    # Mapeamento de critérios de julgamento
    CRITERIOS_JULGAMENTO = {
        "lowestPrice": "Menor Preço",
        "biggestDiscount": "Maior Desconto",
        "biggestPrice": "Maior Preço",
        "bestTechnique": "Melhor Técnica",
        "techniqueAndPrice": "Melhor Técnica e Preço",
        "greaterEconomicReturn": "Maior Retorno Econômico",
    }

    # Mapeamento de tipos de benefício
    TIPOS_BENEFICIO = {
        "noBenefits": "Sem Benefício",
        "isExclusive": "Exclusivo ME/EPP/COOP/MEI",
        "reservedQuota": "Cota Reservada",
        "subcontracting": "Subcontratação",
    }

    def __init__(self, timeout=25, max_retries=2, delay_between_requests=1.0):
        """
        Args:
            timeout: timeout HTTP em segundos
            max_retries: tentativas em caso de erro
            delay_between_requests: segundos entre requisições (respeitar rate limit)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay_between_requests
        self.session = requests.Session()
        self._last_request_time = 0
        self._authenticated = False

        # Configurar URL base
        self.base_url = os.environ.get(
            "LICITAR_PARTNER_BASE_URL", self.DEFAULT_BASE_URL
        ).rstrip("/")

    # ------------------------------------------------------------------ auth

    def autenticar(self, client_id=None, client_secret=None):
        """
        Configura autenticação Basic Auth.

        Args:
            client_id: clientId (ou env LICITAR_PARTNER_CLIENT_ID)
            client_secret: clientSecret (ou env LICITAR_PARTNER_CLIENT_SECRET)

        Returns:
            True se credenciais configuradas com sucesso
        """
        client_id = client_id or os.environ.get("LICITAR_PARTNER_CLIENT_ID", "").strip()
        client_secret = client_secret or os.environ.get("LICITAR_PARTNER_CLIENT_SECRET", "").strip()

        if not client_id or not client_secret:
            logger.warning(
                "Licitar Partner: credenciais não configuradas. "
                "Defina LICITAR_PARTNER_CLIENT_ID e LICITAR_PARTNER_CLIENT_SECRET."
            )
            return False

        # Gerar header Basic Auth: base64(clientId:clientSecret)
        credentials = f"{client_id}:{client_secret}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

        self.session.headers.update({
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        self._authenticated = True
        logger.info(
            "Licitar Partner: autenticado (clientId=%s...)",
            client_id[:8] if len(client_id) > 8 else client_id,
        )
        return True

    # ------------------------------------------------------------------ rate limit

    def _wait_rate_limit(self):
        """Respeita delay entre requisições para não exceder rate limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    # ------------------------------------------------------------------ HTTP

    def _request(self, method, path, params=None, json_data=None):
        """
        Faz requisição HTTP com retry e rate limiting.

        Returns:
            dict com resposta JSON ou None em caso de erro
        """
        if not self._authenticated:
            logger.error("Licitar Partner: não autenticado. Chame autenticar() primeiro.")
            return None

        url = f"{self.base_url}{path}"

        for attempt in range(1, self.max_retries + 1):
            self._wait_rate_limit()

            try:
                self._last_request_time = time.time()
                resp = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=self.timeout,
                )

                if resp.status_code == 429:
                    wait = min(30, 2 ** attempt)
                    logger.warning(
                        "Licitar Partner: rate limit (429). Aguardando %ds...", wait
                    )
                    time.sleep(wait)
                    continue

                if resp.status_code == 401:
                    logger.error("Licitar Partner: não autorizado (401). Verifique credenciais.")
                    return None

                if resp.status_code == 403:
                    logger.error("Licitar Partner: acesso negado (403). Verifique permissões do plano.")
                    return None

                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.Timeout:
                logger.warning(
                    "Licitar Partner: timeout (tentativa %d/%d)", attempt, self.max_retries
                )
            except requests.exceptions.RequestException as exc:
                logger.warning(
                    "Licitar Partner: erro HTTP (tentativa %d/%d): %s",
                    attempt, self.max_retries, exc,
                )

            if attempt < self.max_retries:
                time.sleep(2 ** attempt)

        logger.error("Licitar Partner: falha após %d tentativas em %s", self.max_retries, path)
        return None

    # ================================================================ ENDPOINTS

    # ------------------------------------------------ Processos (Listar)

    def listar_processos(
        self,
        process_type=None,
        state=None,
        published_date=None,
        dispute_date=None,
        organization_doc_number=None,
        include=None,
        limit=100,
        offset=0,
    ):
        """
        Lista processos licitatórios com filtros opcionais.

        Args:
            process_type: Modalidade (E=Pregão, C=Credenciamento, D=Dispensa, R=Concorrência, L=Leilão)
            state: UF (ex: "MG", "SP")
            published_date: Data publicação (YYYY-MM-DD)
            dispute_date: Data disputa (YYYY-MM-DD)
            organization_doc_number: CNPJ do órgão
            include: "lots" para incluir lotes com qtd de propostas
            limit: Registros por página (máx 100)
            offset: Deslocamento de registros

        Returns:
            dict com {status, pagination, data} ou None
        """
        params = {"limit": min(limit, 100), "offset": offset}

        if process_type:
            params["processType"] = process_type
        if state:
            params["state"] = state
        if published_date:
            params["publishedDate"] = published_date
        if dispute_date:
            params["disputeDate"] = dispute_date
        if organization_doc_number:
            params["organizationDocNumber"] = organization_doc_number
        if include:
            params["include"] = include

        return self._request("GET", "/api/v1/partner/process/", params=params)

    # ------------------------------------------------ Processos (Detalhe)

    def obter_processo(self, process_id, include=None):
        """
        Obtém dados completos de um processo (lotes, itens, propostas).

        Args:
            process_id: ID do processo na Licitar Digital
            include: "proposals" para incluir propostas dos fornecedores

        Returns:
            dict com dados do processo ou None
        """
        params = {"id": process_id}
        if include:
            params["include"] = include

        return self._request("GET", "/api/v1/partner/process/", params=params)

    # ------------------------------------------------ Documentos

    def listar_documentos(self, process_id):
        """
        Lista documentos anexados a um processo.

        Args:
            process_id: ID do processo

        Returns:
            dict com documentos ou None
        """
        return self._request(
            "GET", "/api/v1/public/processDocuments",
            params={"processId": process_id},
        )

    # ------------------------------------------------ Chat

    def listar_mensagens_chat(self, process_id, limit=100, offset=0):
        """
        Lista mensagens do chat da sala de disputa.

        Args:
            process_id: ID do processo

        Returns:
            dict com mensagens ou None
        """
        return self._request(
            "GET", "/api/v1/partner/chats/",
            params={"processId": process_id, "limit": limit, "offset": offset},
        )

    # ------------------------------------------------ Fornecedores (Credenciamento)

    def listar_fornecedores(self, process_id, cnpj):
        """
        Lista fornecedores de um processo de Credenciamento.

        Args:
            process_id: ID do processo
            cnpj: CNPJ do Ente Público
        """
        return self._request(
            "GET", "/api/v1/partner/providers-process/",
            params={"processId": process_id, "cnpj": cnpj},
        )

    # ------------------------------------------------ Contratos (Credenciamento)

    def listar_contratos(self, process_id, provider_id):
        """
        Lista contratos de um fornecedor em Credenciamento.

        Args:
            process_id: ID do processo
            provider_id: ID do fornecedor
        """
        return self._request(
            "GET", "/api/v1/partner/contrat-provider-process/",
            params={"processId": process_id, "providerId": provider_id},
        )

    # ------------------------------------------------ Avisos

    def listar_avisos(self, process_id):
        """Busca todos os avisos de um processo."""
        return self._request(
            "GET", "/api/v1/partner/process-notices/",
            params={"id": process_id},
        )

    # ------------------------------------------------ Solicitações

    def listar_solicitacoes(self, process_id, tipo=None):
        """
        Busca solicitações de um processo.

        Args:
            process_id: ID do processo
            tipo: Filtro opcional - "clarifications", "objections", "appeals", "conterReasons"
        """
        params = {"id": process_id}
        if tipo:
            params["type"] = tipo

        return self._request(
            "GET", "/api/v1/partner/process-requests/",
            params=params,
        )

    # ------------------------------------------------ Webhooks

    def cadastrar_webhook(self, process_id, url, headers=None):
        """
        Registra webhook para receber mensagens do chat em tempo real.

        Args:
            process_id: ID do processo
            url: URL pública que receberá os POSTs
            headers: dict com headers customizados para autenticação

        Payload recebido:
            {
                "timestamp": "2025-05-15T12:00:00Z",
                "processId": "4891",
                "sender": "fornecedor 01",
                "message": "Estamos aguardando os lances...",
                "chatId": "98765"
            }
        """
        data = {"processId": process_id, "url": url}
        if headers:
            data["headers"] = headers

        return self._request("POST", "/api/v1/partner/webhooks/", json_data=data)

    def listar_webhooks(self, process_id=None, webhook_id=None):
        """Lista webhooks cadastrados, filtrando por processId ou id."""
        params = {}
        if process_id:
            params["processId"] = process_id
        if webhook_id:
            params["id"] = webhook_id

        return self._request("GET", "/api/v1/partner/webhooks/", params=params)

    def excluir_webhook(self, webhook_id):
        """Exclui um webhook previamente cadastrado."""
        return self._request("DELETE", f"/api/v1/partner/webhooks/{webhook_id}")

    # ================================================================ BUSCA PAGINADA

    def buscar_todos(
        self,
        dias_recentes=7,
        state=None,
        process_type=None,
        max_paginas=10,
        tempo_maximo_seg=120,
    ):
        """
        Busca todos os processos recentes com paginação automática.

        Args:
            dias_recentes: buscar publicados nos últimos N dias
            state: filtrar por UF
            process_type: filtrar por modalidade
            max_paginas: limite de páginas para evitar loop infinito
            tempo_maximo_seg: timeout total da operação

        Returns:
            list de processos (dicts)
        """
        data_inicio = (datetime.now() - timedelta(days=dias_recentes)).strftime("%Y-%m-%d")
        todos = []
        offset = 0
        pagina = 0
        inicio = time.time()

        while pagina < max_paginas:
            if time.time() - inicio > tempo_maximo_seg:
                logger.warning(
                    "Licitar Partner: tempo máximo (%ds) excedido após %d páginas, %d processos",
                    tempo_maximo_seg, pagina, len(todos),
                )
                break

            resp = self.listar_processos(
                process_type=process_type,
                state=state,
                published_date=data_inicio,
                limit=100,
                offset=offset,
            )

            if not resp or resp.get("status") != "success":
                logger.warning("Licitar Partner: resposta inválida na página %d", pagina)
                break

            data = resp.get("data", [])
            if not data:
                break

            todos.extend(data)
            pagina += 1

            # Verificar paginação
            pagination = resp.get("pagination", {})
            total = pagination.get("total", 0)
            next_offset = pagination.get("nextOffset")

            logger.info(
                "Licitar Partner: página %d - %d processos (total: %d)",
                pagina, len(data), total,
            )

            if next_offset is None or next_offset >= total or len(todos) >= total:
                break

            offset = next_offset

        logger.info(
            "Licitar Partner: busca completa - %d processos em %d páginas (%.1fs)",
            len(todos), pagina, time.time() - inicio,
        )
        return todos

    # ================================================================ CONVERSÃO SGL

    @staticmethod
    def converter_para_sgl(processo_raw):
        """
        Converte um processo da API Partner para o formato do banco SGL.

        A API Partner retorna campos em inglês. Este método mapeia para
        os nomes usados no modelo Edital do SGL.

        Args:
            processo_raw: dict retornado pela API Partner

        Returns:
            dict no formato esperado pelo modelo Edital
        """
        # Campos prováveis da API Partner (ajustar conforme resposta real)
        # Os nomes abaixo são baseados na documentação e padrões REST comuns.
        # Se a API retornar campos diferentes, ajustar este mapeamento.

        process_id = str(processo_raw.get("id", ""))
        process_type = processo_raw.get("processType", "")
        modalidade = LicitarPartnerClient.MODALIDADES.get(process_type, process_type)

        # Dados do órgão
        org = processo_raw.get("organization", {}) if isinstance(
            processo_raw.get("organization"), dict
        ) else {}
        orgao_cnpj = (
            org.get("docNumber", "")
            or processo_raw.get("organizationDocNumber", "")
            or ""
        )
        orgao_nome = (
            org.get("name", "")
            or org.get("corporateName", "")
            or processo_raw.get("organizationName", "")
            or ""
        )
        uf = (
            org.get("state", "")
            or processo_raw.get("state", "")
            or ""
        )
        municipio = (
            org.get("city", "")
            or org.get("municipality", "")
            or processo_raw.get("city", "")
            or ""
        )

        # Número do processo/pregão
        numero_processo = processo_raw.get("processNumber", "") or ""
        numero_pregao = processo_raw.get("number", "") or processo_raw.get("noticeNumber", "") or ""

        # Objeto
        objeto = (
            processo_raw.get("object", "")
            or processo_raw.get("description", "")
            or ""
        )

        # Datas
        data_publicacao = processo_raw.get("publishedDate", "") or processo_raw.get("publishDate", "")
        data_disputa = processo_raw.get("disputeDate", "") or processo_raw.get("disputeDateTime", "")
        data_abertura = processo_raw.get("openingDate", "") or processo_raw.get("proposalStartDate", "")
        data_encerramento = processo_raw.get("closingDate", "") or processo_raw.get("proposalEndDate", "")

        # Critério de julgamento
        judgment = processo_raw.get("judgmentCriteria", "")
        criterio = LicitarPartnerClient.CRITERIOS_JULGAMENTO.get(judgment, judgment)

        # SRP
        srp = processo_raw.get("isSRP", False) or processo_raw.get("srp", False)

        # URL do processo na plataforma
        url_plataforma = (
            processo_raw.get("url", "")
            or processo_raw.get("link", "")
            or f"https://app2.licitardigital.com.br/auction-notice/{process_id}"
        )

        # Hash para deduplicação
        hash_input = f"licitardigital:{process_id}:{orgao_cnpj}:{numero_processo}"
        hash_scraper = hashlib.sha256(hash_input.encode()).hexdigest()[:40]

        return {
            "hash_scraper": hash_scraper,
            "id_externo": process_id,
            "numero_pregao": numero_pregao,
            "numero_processo": numero_processo,
            "orgao_cnpj": orgao_cnpj,
            "orgao_razao_social": orgao_nome,
            "unidade_nome": org.get("unitName", "") or orgao_nome,
            "uf": uf,
            "municipio": municipio,
            "objeto_resumo": objeto[:500] if objeto else "",
            "objeto_completo": objeto,
            "modalidade_nome": modalidade,
            "criterio_julgamento": criterio,
            "srp": bool(srp),
            "data_publicacao": data_publicacao,
            "data_abertura_proposta": data_abertura or data_disputa,
            "data_encerramento_proposta": data_encerramento,
            "data_disputa": data_disputa,
            "plataforma_origem": "licitardigital",
            "url_original": url_plataforma,
            "link_sistema_origem": url_plataforma,
            "situacao_pncp": processo_raw.get("status", ""),
            # Dados extras para referência
            "method_dispute": LicitarPartnerClient.METODOS_DISPUTA.get(
                processo_raw.get("methodDispute", ""), ""
            ),
            "type_of_benefit": LicitarPartnerClient.TIPOS_BENEFICIO.get(
                processo_raw.get("typeOfBenefit", ""), ""
            ),
        }

    # ================================================================ UTILIDADES

    def testar_conexao(self):
        """
        Testa se a conexão/credenciais funcionam fazendo uma busca mínima.

        Returns:
            dict com {ok: bool, mensagem: str, detalhes: ...}
        """
        if not self._authenticated:
            return {"ok": False, "mensagem": "Não autenticado. Configure as credenciais."}

        try:
            resp = self.listar_processos(limit=1, offset=0)

            if resp is None:
                return {"ok": False, "mensagem": "Sem resposta da API. Verifique URL e credenciais."}

            if resp.get("status") == "success":
                total = resp.get("pagination", {}).get("total", 0)
                return {
                    "ok": True,
                    "mensagem": f"Conexão OK. {total} processos disponíveis.",
                    "total_processos": total,
                }

            return {
                "ok": False,
                "mensagem": f"Resposta inesperada: {resp.get('status', 'desconhecido')}",
                "detalhes": resp,
            }

        except Exception as exc:
            return {"ok": False, "mensagem": f"Erro: {exc}"}
