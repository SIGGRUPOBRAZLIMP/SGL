"""
SGL - Integração Compras.gov.br

Camada de integração que:
1. Busca contratações na API pública
2. Converte para formato SGL
3. Retorna resultado padronizado para o routes.py

Similar a bbmnet_integration.py
"""
import logging
import os
from datetime import datetime, timedelta

from .comprasgov_client import (
    ComprasGovClient,
    converter_contratacao_14133_para_sgl,
    converter_licitacao_legado_para_sgl,
)

logger = logging.getLogger(__name__)


def executar_captacao_comprasgov(
    app_config=None,
    periodo_dias=None,
    ufs=None,
    modalidade_ids=None,
    incluir_legado=False,
):
    """
    Executa captação completa do Compras.gov.br.

    Args:
        app_config: Flask app config (não usado, mas mantém interface consistente)
        periodo_dias: int dias para trás
        ufs: list[str] UFs para buscar
        modalidade_ids: list[int] IDs de modalidade (Lei 14.133)
        incluir_legado: bool se deve buscar também no módulo legado (Lei 8.666)

    Returns:
        dict com resultados da captação
    """
    resultado = {
        "plataforma": "comprasgov",
        "sucesso": False,
        "mensagem": "",
        "total_encontrados": 0,
        "editais": [],
        "erros": [],
    }

    try:
        # Defaults via .env
        if periodo_dias is None:
            periodo_dias = int(os.environ.get("CAPTACAO_PERIODO_DIAS_DEFAULT", "7"))
        if ufs is None:
            env_ufs = os.environ.get("COMPRASGOV_UFS_DEFAULT", os.environ.get("PNCP_UFS_DEFAULT", "RJ,SP,MG,ES"))
            ufs = [u.strip() for u in env_ufs.split(",") if u.strip()]
        if modalidade_ids is None:
            env_mod = os.environ.get("COMPRASGOV_MODALIDADES_DEFAULT", "4,6,7,8,12")
            modalidade_ids = [int(m.strip()) for m in env_mod.split(",") if m.strip()]

        # Datas
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=periodo_dias)
        data_inicio_str = data_inicio.strftime("%Y%m%d")
        data_fim_str = data_fim.strftime("%Y%m%d")

        logger.info(
            "ComprasGov: Iniciando captação período=%dd, UFs=%s, modalidades=%s",
            periodo_dias, ufs, modalidade_ids,
        )

        client = ComprasGovClient()

        # --- Módulo Contratações (Lei 14.133/2021) ---
        contratacoes_raw = client.buscar_todas_contratacoes(
            data_inicio=data_inicio_str,
            data_fim=data_fim_str,
            modalidades=modalidade_ids,
            ufs=ufs,
        )

        editais_14133 = []
        for c in contratacoes_raw:
            try:
                edital = converter_contratacao_14133_para_sgl(c)
                editais_14133.append(edital)
            except Exception as e:
                resultado["erros"].append(f"Erro converter contratação: {e}")

        logger.info("ComprasGov 14.133: %d editais convertidos", len(editais_14133))

        # --- Módulo Legado (Lei 8.666) - Opcional ---
        editais_legado = []
        if incluir_legado:
            try:
                licitacoes_raw = client.buscar_licitacoes_legado_completo(
                    data_inicio=data_inicio_str,
                    data_fim=data_fim_str,
                    ufs=ufs,
                )
                for lic in licitacoes_raw:
                    try:
                        edital = converter_licitacao_legado_para_sgl(lic)
                        editais_legado.append(edital)
                    except Exception as e:
                        resultado["erros"].append(f"Erro converter legado: {e}")

                logger.info("ComprasGov Legado: %d editais convertidos", len(editais_legado))
            except Exception as e:
                logger.warning("ComprasGov Legado falhou: %s", e)
                resultado["erros"].append(f"Legado: {e}")

        # Consolidar
        todos_editais = editais_14133 + editais_legado

        # Dedup por hash_scraper dentro do batch
        hashes_vistos = set()
        editais_unicos = []
        for ed in todos_editais:
            h = ed.get("hash_scraper", "")
            if h and h not in hashes_vistos:
                hashes_vistos.add(h)
                editais_unicos.append(ed)

        resultado["sucesso"] = True
        resultado["total_encontrados"] = len(editais_unicos)
        resultado["editais"] = editais_unicos
        resultado["mensagem"] = (
            f"ComprasGov: {len(editais_14133)} contratações (14.133)"
            + (f" + {len(editais_legado)} licitações (legado)" if incluir_legado else "")
            + f" = {len(editais_unicos)} únicos"
        )
        logger.info(resultado["mensagem"])

    except Exception as e:
        logger.exception("Erro na captação ComprasGov: %s", e)
        resultado["mensagem"] = f"Erro ComprasGov: {str(e)}"
        resultado["erros"].append(str(e))

    return resultado
