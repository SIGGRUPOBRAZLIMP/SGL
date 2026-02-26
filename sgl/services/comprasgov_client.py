"""
SGL - Client para API Compras.gov.br (Dados Abertos)

API pública, sem autenticação.
Documentação: https://dadosabertos.compras.gov.br/swagger-ui/index.html

Endpoints CORRETOS (verificados via /v3/api-docs em 26/02/2026):
  - /modulo-contratacoes/1_consultarContratacoes_PNCP_14133  (Lei 14.133/2021)
  - /modulo-legado/1_consultarLicitacao                       (Lei 8.666/1993)
  - /modulo-legado/3_consultarPregoes                         (Pregões legado)

Parâmetros OBRIGATÓRIOS:
  - Contratações: dataPublicacaoPncpInicial, dataPublicacaoPncpFinal, codigoModalidade
  - Legado Licitação: data_publicacao_inicial, data_publicacao_final
  - Legado Pregão: dt_data_edital_inicial, dt_data_edital_final
  - Formato de data: YYYY-MM-DD

Autor: SGL Team
"""
import hashlib
import logging
import time
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://dadosabertos.compras.gov.br"

# Mapeamento de modalidades Compras.gov.br → nome legível
MODALIDADES_COMPRASGOV = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão - Presencial",
}

MODOS_DISPUTA = {
    1: "Aberto",
    2: "Fechado",
    3: "Aberto-Fechado",
    4: "Fechado-Aberto",
    5: "Não se aplica",
}


class ComprasGovClient:
    """Client para API de Dados Abertos do Compras.gov.br"""

    def __init__(self, timeout=25, max_retries=2, delay=0.3):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "SGL-CaptacaoEditais/1.0",
        })
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay
        self._last_request = 0

    def _rate_limit(self):
        diff = time.time() - self._last_request
        if diff < self.delay:
            time.sleep(self.delay - diff)
        self._last_request = time.time()

    def _get(self, path, params=None):
        """GET genérico com rate limit e retry"""
        self._rate_limit()
        url = f"{BASE_URL}{path}"
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    logger.warning("Rate limited, aguardando %ds...", wait)
                    time.sleep(wait)
                    continue
                else:
                    logger.error(
                        "ComprasGov HTTP %d para %s params=%s: %s",
                        resp.status_code, path, params, resp.text[:300],
                    )
                    return None
            except requests.exceptions.Timeout:
                logger.warning(
                    "Timeout tentativa %d/%d para %s",
                    attempt + 1, self.max_retries, path,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(1)
            except Exception as e:
                logger.error("Erro ComprasGov: %s", e)
                return None
        return None

    # ================================================================
    # MÓDULO CONTRATAÇÕES - Lei 14.133/2021
    # Path: /modulo-contratacoes/1_consultarContratacoes_PNCP_14133
    # ================================================================

    def consultar_contratacoes_14133(
        self,
        data_publicacao_inicio,
        data_publicacao_fim,
        codigo_modalidade,
        uf=None,
        orgao_cnpj=None,
        codigo_ibge=None,
        pagina=1,
        tamanho_pagina=500,
    ):
        """
        Consulta contratações pela nova lei (14.133/2021).

        Parâmetros OBRIGATÓRIOS pela API:
            data_publicacao_inicio: str formato YYYY-MM-DD
            data_publicacao_fim: str formato YYYY-MM-DD
            codigo_modalidade: int (1-13, ver MODALIDADES_COMPRASGOV)

        Parâmetros opcionais:
            uf: str (sigla UF, ex: "RJ") → unidadeOrgaoUfSigla
            orgao_cnpj: str (CNPJ do órgão)
            codigo_ibge: int (código IBGE do município)
        """
        params = {
            "pagina": pagina,
            "tamanhoPagina": min(tamanho_pagina, 500),
            # Obrigatórios
            "dataPublicacaoPncpInicial": data_publicacao_inicio,
            "dataPublicacaoPncpFinal": data_publicacao_fim,
            "codigoModalidade": codigo_modalidade,
        }
        if uf:
            params["unidadeOrgaoUfSigla"] = uf
        if orgao_cnpj:
            params["orgaoEntidadeCnpj"] = orgao_cnpj
        if codigo_ibge:
            params["unidadeOrgaoCodigoIbge"] = codigo_ibge

        return self._get(
            "/modulo-contratacoes/1_consultarContratacoes_PNCP_14133",
            params,
        )

    # ================================================================
    # MÓDULO LEGADO - Lei 8.666/1993
    # ================================================================

    def consultar_licitacoes_legado(
        self,
        data_publicacao_inicial,
        data_publicacao_final,
        modalidade=None,
        uasg=None,
        pagina=1,
        tamanho_pagina=500,
    ):
        """
        Consulta licitações pelo módulo legado.

        Parâmetros OBRIGATÓRIOS:
            data_publicacao_inicial: str formato YYYY-MM-DD
            data_publicacao_final: str formato YYYY-MM-DD
        """
        params = {
            "pagina": pagina,
            "tamanhoPagina": min(tamanho_pagina, 500),
            "data_publicacao_inicial": data_publicacao_inicial,
            "data_publicacao_final": data_publicacao_final,
        }
        if modalidade:
            params["modalidade"] = modalidade
        if uasg:
            params["uasg"] = uasg

        return self._get("/modulo-legado/1_consultarLicitacao", params)

    def consultar_pregoes_legado(
        self,
        data_edital_inicial,
        data_edital_final,
        co_uasg=None,
        pagina=1,
        tamanho_pagina=500,
    ):
        """
        Consulta pregões pelo módulo legado.

        Parâmetros OBRIGATÓRIOS:
            data_edital_inicial: str formato YYYY-MM-DD
            data_edital_final: str formato YYYY-MM-DD
        """
        params = {
            "pagina": pagina,
            "tamanhoPagina": min(tamanho_pagina, 500),
            "dt_data_edital_inicial": data_edital_inicial,
            "dt_data_edital_final": data_edital_final,
        }
        if co_uasg:
            params["co_uasg"] = co_uasg

        return self._get("/modulo-legado/3_consultarPregoes", params)

    # ================================================================
    # BUSCA PAGINADA COMPLETA (com orçamento de tempo)
    # ================================================================

    def buscar_todas_contratacoes(
        self,
        data_inicio,
        data_fim,
        modalidades=None,
        ufs=None,
        max_paginas=20,
        tempo_maximo_seg=90,
    ):
        """
        Busca completa com paginação, iterando por Modalidade × UF.

        codigoModalidade é OBRIGATÓRIO, então iteramos por modalidade.
        UF é opcional.

        Inclui orçamento de tempo (tempo_maximo_seg) para não estourar
        o timeout do Gunicorn (~120s no Render).

        Args:
            data_inicio: str YYYY-MM-DD
            data_fim: str YYYY-MM-DD
            modalidades: list[int] IDs de modalidade
            ufs: list[str] UFs a buscar (None = todas)
            max_paginas: int máximo de páginas por combinação
            tempo_maximo_seg: int tempo máximo total em segundos
        """
        if modalidades is None:
            modalidades = [4, 6, 7, 8, 12]

        uf_list = ufs if ufs else [None]
        todas = []
        inicio_exec = time.time()
        abortado = False

        for uf in uf_list:
            if abortado:
                break
            for mod_id in modalidades:
                # Checar orçamento de tempo antes de cada modalidade
                elapsed = time.time() - inicio_exec
                if elapsed >= tempo_maximo_seg:
                    logger.warning(
                        "ComprasGov: orçamento de tempo esgotado (%.0fs). "
                        "Captados %d registros até agora.",
                        elapsed, len(todas),
                    )
                    abortado = True
                    break

                pagina = 1
                while pagina <= max_paginas:
                    # Checar orçamento antes de cada página
                    if (time.time() - inicio_exec) >= tempo_maximo_seg:
                        logger.warning(
                            "ComprasGov: orçamento de tempo esgotado durante paginação."
                        )
                        abortado = True
                        break

                    resultado = self.consultar_contratacoes_14133(
                        data_publicacao_inicio=data_inicio,
                        data_publicacao_fim=data_fim,
                        codigo_modalidade=mod_id,
                        uf=uf,
                        pagina=pagina,
                        tamanho_pagina=500,
                    )

                    if not resultado:
                        break

                    registros = resultado.get("resultado", [])
                    total_reg = resultado.get("totalRegistros", 0)
                    paginas_rest = resultado.get("paginasRestantes", 0)

                    if registros:
                        todas.extend(registros)
                        logger.info(
                            "ComprasGov: UF=%s MOD=%d pag=%d → %d reg (total=%d)",
                            uf, mod_id, pagina, len(registros), total_reg,
                        )

                    if paginas_rest <= 0 or not registros:
                        break
                    pagina += 1

        elapsed_total = time.time() - inicio_exec
        logger.info(
            "ComprasGov: total bruto = %d contratações em %.1fs%s",
            len(todas), elapsed_total,
            " (parcial - tempo esgotado)" if abortado else "",
        )
        return todas

    def buscar_licitacoes_legado_completo(
        self,
        data_inicio,
        data_fim,
        ufs=None,
        max_paginas=10,
    ):
        """Busca licitações do módulo legado com paginação."""
        todas = []
        pagina = 1
        while pagina <= max_paginas:
            resultado = self.consultar_licitacoes_legado(
                data_publicacao_inicial=data_inicio,
                data_publicacao_final=data_fim,
                pagina=pagina,
            )
            if not resultado:
                break

            registros = resultado.get("resultado", [])
            paginas_rest = resultado.get("paginasRestantes", 0)

            if registros:
                todas.extend(registros)
                logger.info(
                    "ComprasGov Legado: pag=%d → %d registros",
                    pagina, len(registros),
                )

            if paginas_rest <= 0 or not registros:
                break
            pagina += 1

        logger.info("ComprasGov Legado: total bruto = %d licitações", len(todas))
        return todas


# ================================================================
# CONVERSOR: dados da API → formato SGL
# ================================================================

def converter_contratacao_14133_para_sgl(contratacao):
    """
    Converte contratação (schema VwFtPNCPCompra) para formato SGL.
    """
    numero = contratacao.get("numeroCompra", "")
    ano = contratacao.get("anoCompraPncp", "")
    cnpj = contratacao.get("orgaoEntidadeCnpj", "")
    uasg = contratacao.get("unidadeOrgaoCodigoUnidade", "")

    hash_str = f"comprasgov:{cnpj}:{uasg}:{numero}:{ano}"
    hash_scraper = hashlib.md5(hash_str.encode()).hexdigest()

    modalidade_id = contratacao.get("codigoModalidade") or contratacao.get("modalidadeIdPncp")
    modalidade_nome = (
        contratacao.get("modalidadeNome")
        or MODALIDADES_COMPRASGOV.get(modalidade_id, f"Modalidade {modalidade_id}")
    )

    uf = contratacao.get("unidadeOrgaoUfSigla", "")
    municipio = contratacao.get("unidadeOrgaoMunicipioNome", "")

    numero_controle = contratacao.get("numeroControlePNCP", "")
    link_pncp = f"https://pncp.gov.br/app/editais/{numero_controle}" if numero_controle else ""

    srp = contratacao.get("srp", False)
    objeto = contratacao.get("objetoCompra", "") or ""
    if not srp and "registro de pre" in objeto.lower():
        srp = True

    numero_display = f"{numero}/{ano}" if numero and ano else str(numero)

    return {
        "hash_scraper": hash_scraper,
        "numero_pregao": numero_display,
        "numero_processo": contratacao.get("processo", numero_display),
        "orgao_cnpj": cnpj,
        "orgao_razao_social": contratacao.get("orgaoEntidadeRazaoSocial", ""),
        "unidade_nome": contratacao.get("unidadeOrgaoNomeUnidade", ""),
        "uf": uf,
        "municipio": municipio,
        "objeto_resumo": objeto[:500] if objeto else "",
        "objeto_completo": objeto,
        "modalidade_nome": modalidade_nome,
        "modalidade_id_comprasgov": modalidade_id,
        "srp": srp,
        "data_publicacao": contratacao.get("dataPublicacaoPncp"),
        "data_abertura_proposta": contratacao.get("dataAberturaPropostaPncp"),
        "data_encerramento_proposta": contratacao.get("dataEncerramentoPropostaPncp"),
        "valor_estimado": contratacao.get("valorTotalEstimado"),
        "plataforma_origem": "comprasgov",
        "url_original": link_pncp,
        "link_sistema_origem": "",
        "link_pncp": link_pncp,
        "situacao_pncp": contratacao.get("situacaoCompraNomePncp", ""),
        "status": "captado",
    }


def converter_licitacao_legado_para_sgl(licitacao):
    """
    Converte licitação legado (schema TbVwLicitacaoDTO) para formato SGL.
    """
    id_compra = licitacao.get("id_compra", "")
    num_aviso = licitacao.get("numero_aviso", "")
    num_processo = licitacao.get("numero_processo", "")
    uasg = licitacao.get("uasg", "")

    hash_str = f"comprasgovlegado:{id_compra}:{uasg}:{num_aviso}"
    hash_scraper = hashlib.md5(hash_str.encode()).hexdigest()

    objeto = licitacao.get("objeto", "") or ""
    srp = "registro de pre" in objeto.lower()

    return {
        "hash_scraper": hash_scraper,
        "numero_pregao": str(num_aviso) if num_aviso else "",
        "numero_processo": num_processo,
        "orgao_cnpj": None,
        "orgao_razao_social": "",
        "unidade_nome": "",
        "uf": "",
        "municipio": "",
        "objeto_resumo": objeto[:500],
        "objeto_completo": objeto,
        "modalidade_nome": licitacao.get("nome_modalidade", ""),
        "srp": srp,
        "data_publicacao": licitacao.get("data_publicacao"),
        "data_abertura_proposta": licitacao.get("data_abertura_proposta"),
        "data_encerramento_proposta": None,
        "valor_estimado": licitacao.get("valor_estimado_total"),
        "plataforma_origem": "comprasgov_legado",
        "url_original": "",
        "link_sistema_origem": "",
        "situacao_pncp": licitacao.get("situacao_aviso", ""),
        "status": "captado",
    }
