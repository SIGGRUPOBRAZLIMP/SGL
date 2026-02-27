"""
SGL - Integração Compras.gov.br

Busca contratações via API Dados Abertos e SALVA no banco SGL.
Formato de data: YYYY-MM-DD
Endpoints do Swagger: https://dadosabertos.compras.gov.br/swagger-ui/index.html
"""
import logging
import os
from datetime import datetime, timedelta

from flask import current_app

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
    Executa captação completa do Compras.gov.br e persiste no banco.

    Returns:
        dict com {total_encontrados, novos_salvos, duplicados, erros, plataforma}
    """
    stats = {
        "plataforma": "comprasgov",
        "total_encontrados": 0,
        "novos_salvos": 0,
        "duplicados": 0,
        "erros": 0,
        "mensagem": "",
    }

    try:
        # Defaults via .env
        if periodo_dias is None:
            periodo_dias = int(os.environ.get("CAPTACAO_PERIODO_DIAS_DEFAULT", "7"))
        if ufs is None:
            env_ufs = os.environ.get(
                "COMPRASGOV_UFS_DEFAULT",
                os.environ.get("PNCP_UFS_DEFAULT", "RJ,SP,MG,ES"),
            )
            ufs = [u.strip() for u in env_ufs.split(",") if u.strip()]
        if modalidade_ids is None:
            env_mod = os.environ.get("COMPRASGOV_MODALIDADES_DEFAULT", "4,6,7,8,12")
            modalidade_ids = [int(m.strip()) for m in env_mod.split(",") if m.strip()]

        # Datas no formato YYYY-MM-DD (obrigatório pela API)
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=periodo_dias)
        data_inicio_str = data_inicio.strftime("%Y-%m-%d")
        data_fim_str = data_fim.strftime("%Y-%m-%d")

        logger.info(
            "ComprasGov: Iniciando captação período=%s a %s, UFs=%s, modalidades=%s",
            data_inicio_str, data_fim_str, ufs, modalidade_ids,
        )

        client = ComprasGovClient()

        # --- Módulo Contratações (Lei 14.133/2021) ---
        contratacoes_raw = client.buscar_todas_contratacoes(
            data_inicio=data_inicio_str,
            data_fim=data_fim_str,
            modalidades=modalidade_ids,
            ufs=ufs,
        )

        editais_convertidos = []
        for c in contratacoes_raw:
            try:
                edital = converter_contratacao_14133_para_sgl(c)
                editais_convertidos.append(edital)
            except Exception as e:
                stats["erros"] += 1
                logger.warning("Erro converter contratação ComprasGov: %s", e)

        logger.info("ComprasGov 14.133: %d editais convertidos", len(editais_convertidos))

        # --- Módulo Legado (Lei 8.666) - Opcional ---
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
                        editais_convertidos.append(edital)
                    except Exception as e:
                        stats["erros"] += 1
                        logger.warning("Erro converter legado ComprasGov: %s", e)

                logger.info("ComprasGov Legado: %d editais adicionados", len(licitacoes_raw))
            except Exception as e:
                logger.warning("ComprasGov Legado falhou: %s", e)
                stats["erros"] += 1

        # Dedup interno (dentro do batch)
        hashes_vistos = set()
        editais_unicos = []
        for ed in editais_convertidos:
            h = ed.get("hash_scraper", "")
            if h and h not in hashes_vistos:
                hashes_vistos.add(h)
                editais_unicos.append(ed)

        stats["total_encontrados"] = len(editais_unicos)

        if not editais_unicos:
            stats["mensagem"] = (
                f"ComprasGov: 0 contratações ({len(contratacoes_raw)}) = 0 únicos"
            )
            logger.info(stats["mensagem"])
            return stats

        # ========== SALVAR NO BANCO ==========
        from .. import db
        from ..models import Edital, Triagem

        for edital_sgl in editais_unicos:
            try:
                hash_scraper = edital_sgl.get("hash_scraper")

                # Dedup por hash_scraper
                if hash_scraper:
                    existente = Edital.query.filter_by(hash_scraper=hash_scraper).first()
                    if existente:
                        stats["duplicados"] += 1
                        continue

                # Dedup por processo + orgao + plataforma
                orgao = edital_sgl.get("orgao_razao_social")
                processo = edital_sgl.get("numero_processo")
                if orgao and processo:
                    existente = Edital.query.filter_by(
                        orgao_razao_social=orgao,
                        numero_processo=processo,
                        plataforma_origem="comprasgov",
                    ).first()
                    if existente:
                        stats["duplicados"] += 1
                        continue

                # Parse datas
                def _parse_dt(s):
                    if not s:
                        return None
                    try:
                        clean = s.replace("Z", "").split("+")[0].split("-03:00")[0]
                        return datetime.fromisoformat(clean)
                    except (ValueError, TypeError):
                        return None

                edital = Edital(
                    hash_scraper=hash_scraper,
                    numero_pregao=edital_sgl.get("numero_pregao"),
                    numero_processo=edital_sgl.get("numero_processo"),
                    orgao_cnpj=edital_sgl.get("orgao_cnpj"),
                    orgao_razao_social=edital_sgl.get("orgao_razao_social"),
                    unidade_nome=edital_sgl.get("unidade_nome"),
                    uf=edital_sgl.get("uf"),
                    municipio=edital_sgl.get("municipio"),
                    objeto_resumo=edital_sgl.get("objeto_resumo"),
                    objeto_completo=edital_sgl.get("objeto_completo"),
                    modalidade_nome=edital_sgl.get("modalidade_nome"),
                    srp=edital_sgl.get("srp", False),
                    data_publicacao=_parse_dt(edital_sgl.get("data_publicacao")),
                    data_abertura_proposta=_parse_dt(edital_sgl.get("data_abertura_proposta")),
                    data_encerramento_proposta=_parse_dt(edital_sgl.get("data_encerramento_proposta")),
                    valor_estimado=edital_sgl.get("valor_estimado"),
                    plataforma_origem="comprasgov",
                    url_original=edital_sgl.get("url_original"),
                    link_sistema_origem=edital_sgl.get("link_sistema_origem"),
                    situacao_pncp=edital_sgl.get("situacao_pncp"),
                    status="captado",
                )
                db.session.add(edital)
                db.session.flush()

                # Criar triagem automática
                triagem = Triagem(
                    edital_id=edital.id,
                    decisao="pendente",
                    prioridade="media",
                )
                db.session.add(triagem)
                db.session.commit()

                stats["novos_salvos"] += 1

            except Exception as exc:
                db.session.rollback()
                logger.error(
                    "Erro salvar edital ComprasGov hash=%s: %s",
                    edital_sgl.get("hash_scraper", "?"), exc,
                )
                stats["erros"] += 1

        stats["mensagem"] = (
            f"ComprasGov: {stats['total_encontrados']} encontrados, "
            f"{stats['novos_salvos']} novos, {stats['duplicados']} duplicados, "
            f"{stats['erros']} erros"
        )
        logger.info(stats["mensagem"])

    except Exception as e:
        logger.exception("Erro na captação ComprasGov: %s", e)
        stats["mensagem"] = f"Erro ComprasGov: {str(e)}"
        stats["erros"] += 1

    return stats
