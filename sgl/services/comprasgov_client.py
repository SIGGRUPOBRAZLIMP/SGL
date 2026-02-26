"""
SGL - Client para API Compras.gov.br (Dados Abertos)

API pública, sem autenticação.
Documentação: https://dadosabertos.compras.gov.br/swagger-ui/index.html
Manual: https://www.gov.br/compras/pt-br/acesso-a-informacao/manuais/manual-dados-abertos/manual-api-compras.pdf

Dois módulos relevantes:
  - Módulo Contratações (Lei 14.133/2021): /modulo-contratacao/
  - Módulo Legado (Lei 8.666/1993): /modulo-legado/

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
    # Lei 14.133/2021 (Módulo Contratações)
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

# Modos de disputa
MODOS_DISPUTA = {
    1: "Aberto",
    2: "Fechado",
    3: "Aberto-Fechado",
    4: "Fechado-Aberto",
    5: "Não se aplica",
}


class ComprasGovClient:
    """Client para API de Dados Abertos do Compras.gov.br"""

    def __init__(self, timeout=60, delay=0.3):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "SGL-CaptacaoEditais/1.0",
        })
        self.timeout = timeout
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
        for attempt in range(3):
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
                    logger.error("ComprasGov HTTP %d: %s", resp.status_code, resp.text[:200])
                    return None
            except requests.exceptions.Timeout:
                logger.warning("Timeout tentativa %d/3 para %s", attempt + 1, path)
                if attempt < 2:
                    time.sleep(2)
            except Exception as e:
                logger.error("Erro ComprasGov: %s", e)
                return None
        return None

    # ================================================================
    # MÓDULO CONTRATAÇÕES - Lei 14.133/2021
    # ================================================================

    def consultar_contratacoes_14133(
        self,
        data_publicacao_inicio=None,
        data_publicacao_fim=None,
        modalidade_id=None,
        uf=None,
        orgao_cnpj=None,
        pagina=1,
        tamanho_pagina=50,
    ):
        """
        Consulta contratações pela nova lei (14.133/2021).

        Endpoint: /modulo-contratacao/1_consultarContratacao
        Sem autenticação.

        Parâmetros:
            data_publicacao_inicio: str formato YYYYMMDD
            data_publicacao_fim: str formato YYYYMMDD
            modalidade_id: int (1-13, ver MODALIDADES_COMPRASGOV)
            uf: str (sigla UF, ex: "RJ")
            orgao_cnpj: str (CNPJ do órgão)
            pagina: int
            tamanho_pagina: int (max 500)
        """
        params = {"pagina": pagina}
        if tamanho_pagina:
            params["tamanhoPagina"] = min(tamanho_pagina, 500)
        if data_publicacao_inicio:
            params["dataPublicacaoInicio"] = data_publicacao_inicio
        if data_publicacao_fim:
            params["dataPublicacaoFim"] = data_publicacao_fim
        if modalidade_id:
            params["modalidadeId"] = modalidade_id
        if uf:
            params["uf"] = uf
        if orgao_cnpj:
            params["orgaoEntidadeCnpj"] = orgao_cnpj

        return self._get("/modulo-contratacao/1_consultarContratacao", params)

    def consultar_itens_contratacao_14133(
        self,
        numero_compra=None,
        ano_compra=None,
        codigo_uasg=None,
        pagina=1,
    ):
        """Consulta itens de uma contratação específica"""
        params = {"pagina": pagina}
        if numero_compra:
            params["numeroCompra"] = numero_compra
        if ano_compra:
            params["anoCompra"] = ano_compra
        if codigo_uasg:
            params["codigoUasg"] = codigo_uasg

        return self._get("/modulo-contratacao/2_consultarItemContratacao", params)

    # ================================================================
    # MÓDULO LEGADO - Lei 8.666/1993
    # ================================================================

    def consultar_licitacoes_legado(
        self,
        uf=None,
        modalidade=None,
        data_abertura_inicio=None,
        data_abertura_fim=None,
        pagina=1,
    ):
        """
        Consulta licitações pelo módulo legado (leis anteriores à 14.133).

        Endpoint: /modulo-legado/1_consultarLicitacao
        """
        params = {"pagina": pagina}
        if uf:
            params["uf"] = uf
        if modalidade:
            params["modalidade"] = modalidade
        if data_abertura_inicio:
            params["dataAberturaInicio"] = data_abertura_inicio
        if data_abertura_fim:
            params["dataAberturaFim"] = data_abertura_fim

        return self._get("/modulo-legado/1_consultarLicitacao", params)

    def consultar_pregoes_legado(
        self,
        uf=None,
        data_abertura_inicio=None,
        data_abertura_fim=None,
        pagina=1,
    ):
        """
        Consulta pregões pelo módulo legado.

        Endpoint: /modulo-legado/3_consultarPregao
        """
        params = {"pagina": pagina}
        if uf:
            params["uf"] = uf
        if data_abertura_inicio:
            params["dataAberturaInicio"] = data_abertura_inicio
        if data_abertura_fim:
            params["dataAberturaFim"] = data_abertura_fim

        return self._get("/modulo-legado/3_consultarPregao", params)

    # ================================================================
    # BUSCA PAGINADA COMPLETA
    # ================================================================

    def buscar_todas_contratacoes(
        self,
        data_inicio,
        data_fim,
        modalidades=None,
        ufs=None,
        max_paginas=20,
    ):
        """
        Busca completa com paginação, iterando por UF × Modalidade.

        Args:
            data_inicio: str YYYYMMDD
            data_fim: str YYYYMMDD
            modalidades: list[int] IDs de modalidade (default: todas principais)
            ufs: list[str] UFs a buscar
            max_paginas: int máximo de páginas por combinação

        Returns:
            list[dict] contratações brutas da API
        """
        if modalidades is None:
            modalidades = [4, 6, 7, 8, 12]  # Concorrência E, Pregão E/P, Dispensa, Credenciamento
        if ufs is None:
            ufs = ["RJ", "SP", "MG", "ES"]

        todas = []
        total_api = 0

        for uf in ufs:
            for mod_id in modalidades:
                pagina = 1
                while pagina <= max_paginas:
                    resultado = self.consultar_contratacoes_14133(
                        data_publicacao_inicio=data_inicio,
                        data_publicacao_fim=data_fim,
                        modalidade_id=mod_id,
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
                        total_api += len(registros)
                        logger.info(
                            "ComprasGov: UF=%s MOD=%d pag=%d → %d registros (total API: %d)",
                            uf, mod_id, pagina, len(registros), total_reg,
                        )

                    if paginas_rest <= 0 or not registros:
                        break
                    pagina += 1

        logger.info("ComprasGov: total bruto captado = %d contratações", len(todas))
        return todas

    def buscar_licitacoes_legado_completo(
        self,
        data_inicio,
        data_fim,
        ufs=None,
        max_paginas=10,
    ):
        """Busca licitações do módulo legado (Lei 8.666) com paginação."""
        if ufs is None:
            ufs = ["RJ", "SP", "MG", "ES"]

        todas = []
        for uf in ufs:
            pagina = 1
            while pagina <= max_paginas:
                resultado = self.consultar_licitacoes_legado(
                    uf=uf,
                    data_abertura_inicio=data_inicio,
                    data_abertura_fim=data_fim,
                    pagina=pagina,
                )
                if not resultado:
                    break

                registros = resultado.get("resultado", [])
                paginas_rest = resultado.get("paginasRestantes", 0)

                if registros:
                    todas.extend(registros)
                    logger.info(
                        "ComprasGov Legado: UF=%s pag=%d → %d registros",
                        uf, pagina, len(registros),
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
    Converte uma contratação do módulo 14.133 para o formato de edital SGL.

    Campos esperados da API (baseado no Swagger):
        - numeroCompra, anoCompra
        - orgaoEntidadeCnpj, orgaoEntidadeRazaoSocial
        - unidadeOrgaoCodigoUasg, unidadeOrgaoNomeUnidade
        - objetoCompra
        - modalidadeId, modalidadeNome
        - modoDisputaId, modoDisputaNome
        - dataPublicacao, dataAberturaProposta, dataEncerramentoProposta
        - situacaoCompra (ex: "Aberta", "Publicada", "Homologada", etc.)
        - ufSigla, municipioNome
        - valorEstimado, srp (boolean)
        - linkSistemaOrigem, linkPncp
    """
    numero = contratacao.get("numeroCompra", "")
    ano = contratacao.get("anoCompra", "")
    cnpj = contratacao.get("orgaoEntidadeCnpj", "")
    uasg = contratacao.get("unidadeOrgaoCodigoUasg", "")

    # Hash único para dedup
    hash_str = f"comprasgov:{cnpj}:{uasg}:{numero}:{ano}"
    hash_scraper = hashlib.md5(hash_str.encode()).hexdigest()

    modalidade_id = contratacao.get("modalidadeId")
    modalidade_nome = contratacao.get("modalidadeNome") or MODALIDADES_COMPRASGOV.get(modalidade_id, f"Modalidade {modalidade_id}")

    uf = contratacao.get("ufSigla", "")
    municipio = contratacao.get("municipioNome", "")

    # URLs
    link_pncp = contratacao.get("linkPncp", "")
    link_sistema = contratacao.get("linkSistemaOrigem", "")
    url_principal = link_pncp or link_sistema or ""

    # SRP
    srp = contratacao.get("srp", False)
    objeto = contratacao.get("objetoCompra", "") or ""
    if not srp and "registro de pre" in objeto.lower():
        srp = True

    numero_display = f"{numero}/{ano}" if numero and ano else str(numero)

    return {
        "hash_scraper": hash_scraper,
        "numero_pregao": numero_display,
        "numero_processo": contratacao.get("processoCompra", numero_display),
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
        "data_publicacao": contratacao.get("dataPublicacao"),
        "data_abertura_proposta": contratacao.get("dataAberturaProposta"),
        "data_encerramento_proposta": contratacao.get("dataEncerramentoProposta"),
        "valor_estimado": contratacao.get("valorEstimado"),
        "plataforma_origem": "comprasgov",
        "url_original": url_principal,
        "link_sistema_origem": link_sistema,
        "link_pncp": link_pncp,
        "situacao_pncp": contratacao.get("situacaoCompra", ""),
        "status": "captado",
    }


def converter_licitacao_legado_para_sgl(licitacao):
    """
    Converte licitação do módulo legado (8.666) para formato SGL.

    Campos esperados da API:
        - licitacaoId, numPregao, numProcesso
        - uasgNome, uasgCodigo
        - objetoLicitacao
        - modalidadeLicitacao
        - dataAbertura, dataPublicacao
        - situacao
        - ufSigla
    """
    lic_id = licitacao.get("licitacaoId", "")
    num_pregao = licitacao.get("numPregao", "")
    num_processo = licitacao.get("numProcesso", "")
    uasg = licitacao.get("uasgCodigo", "")

    hash_str = f"comprasgovlegado:{lic_id}:{uasg}:{num_pregao}"
    hash_scraper = hashlib.md5(hash_str.encode()).hexdigest()

    objeto = licitacao.get("objetoLicitacao", "") or ""
    srp = "registro de pre" in objeto.lower()

    return {
        "hash_scraper": hash_scraper,
        "numero_pregao": num_pregao,
        "numero_processo": num_processo,
        "orgao_cnpj": None,
        "orgao_razao_social": licitacao.get("uasgNome", ""),
        "unidade_nome": licitacao.get("uasgNome", ""),
        "uf": licitacao.get("ufSigla", ""),
        "municipio": "",
        "objeto_resumo": objeto[:500],
        "objeto_completo": objeto,
        "modalidade_nome": licitacao.get("modalidadeLicitacao", ""),
        "srp": srp,
        "data_publicacao": licitacao.get("dataPublicacao"),
        "data_abertura_proposta": licitacao.get("dataAbertura"),
        "data_encerramento_proposta": None,
        "plataforma_origem": "comprasgov_legado",
        "url_original": f"https://www.gov.br/compras/pt-br/acesso-a-informacao/consulta-detalhada",
        "link_sistema_origem": "",
        "situacao_pncp": licitacao.get("situacao", ""),
        "status": "captado",
    }
