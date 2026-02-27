"""
SGL - Integração Licitar Digital (API Partner Oficial)
======================================================
Conecta o LicitarPartnerClient ao banco de dados SGL.
Chamado pelo botão "Captar" no frontend e pelo scheduler.

Modo de operação:
  - API Partner oficial com Basic Auth (clientId:clientSecret)
  - Funciona direto do Render — sem Cloudflare, sem script local
  - Rate limit: 60 req/min, paginação limit/offset

Variáveis de ambiente necessárias:
  LICITAR_PARTNER_CLIENT_ID
  LICITAR_PARTNER_CLIENT_SECRET
  LICITAR_PARTNER_BASE_URL (opcional — informado no onboarding)
"""

import logging
import os
from datetime import datetime

from flask import current_app

logger = logging.getLogger(__name__)


def executar_captacao_licitardigital(app_config=None, periodo_dias=7):
    """
    Executa captação de editais do Licitar Digital via API Partner e salva no banco SGL.

    Args:
        app_config: configuração Flask (opcional)
        periodo_dias: quantos dias para trás buscar

    Returns:
        dict com estatísticas: {total, novos_salvos, duplicados, erros, plataforma, modo}
    """
    from .licitardigital_partner_client import LicitarPartnerClient

    stats = {
        "total": 0,
        "novos_salvos": 0,
        "duplicados": 0,
        "erros": 0,
        "plataforma": "licitardigital",
        "modo": "api_partner",
    }

    # Criar cliente
    client = LicitarPartnerClient(timeout=25, max_retries=3, delay_between_requests=1.0)

    # Autenticar
    client_id = os.environ.get("LICITAR_PARTNER_CLIENT_ID", "").strip()
    client_secret = os.environ.get("LICITAR_PARTNER_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        logger.warning("Licitar Partner: credenciais não configuradas")
        stats["erros"] = 1
        stats["mensagem"] = (
            "Configure LICITAR_PARTNER_CLIENT_ID e LICITAR_PARTNER_CLIENT_SECRET "
            "no Render. Obtenha as credenciais em integracoes@licitardigital.com.br"
        )
        return stats

    if not client.autenticar(client_id=client_id, client_secret=client_secret):
        stats["erros"] = 1
        stats["mensagem"] = "Falha na autenticação com API Partner."
        return stats

    # Buscar processos
    try:
        processos_raw = client.buscar_todos(
            dias_recentes=periodo_dias,
            max_paginas=10,
            tempo_maximo_seg=120,
        )
    except Exception as exc:
        logger.error("Licitar Partner busca falhou: %s", exc)
        stats["erros"] = 1
        stats["mensagem"] = f"Erro na busca: {exc}"
        return stats

    if not processos_raw:
        logger.info(
            "Licitar Partner: nenhum processo encontrado nos últimos %d dias",
            periodo_dias,
        )
        stats["mensagem"] = f"Nenhum processo encontrado nos últimos {periodo_dias} dias"
        return stats

    stats["total"] = len(processos_raw)

    # Salvar no banco
    from .. import db
    from ..models import Edital, Triagem

    for proc_raw in processos_raw:
        try:
            edital_sgl = LicitarPartnerClient.converter_para_sgl(proc_raw)
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
                    plataforma_origem="licitardigital",
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
                plataforma_origem="licitardigital",
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
                "Erro salvar processo Licitar Partner #%s: %s",
                proc_raw.get("id"), exc,
            )
            stats["erros"] += 1

    logger.info(
        "Licitar Partner: %d encontrados, %d novos, %d duplicados, %d erros",
        stats["total"], stats["novos_salvos"], stats["duplicados"], stats["erros"],
    )
    return stats


def testar_conexao_licitardigital():
    """
    Testa conexão com a API Partner.
    Útil para validar credenciais no painel admin.

    Returns:
        dict com {ok: bool, mensagem: str}
    """
    from .licitardigital_partner_client import LicitarPartnerClient

    client = LicitarPartnerClient(timeout=15, max_retries=1)

    client_id = os.environ.get("LICITAR_PARTNER_CLIENT_ID", "").strip()
    client_secret = os.environ.get("LICITAR_PARTNER_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        return {
            "ok": False,
            "mensagem": "Credenciais não configuradas (LICITAR_PARTNER_CLIENT_ID / SECRET)",
        }

    if not client.autenticar(client_id=client_id, client_secret=client_secret):
        return {"ok": False, "mensagem": "Falha ao configurar autenticação"}

    return client.testar_conexao()
