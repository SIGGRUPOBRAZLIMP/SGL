"""
SGL - Integração Licitar Digital → Banco de dados SGL
"""
import logging
import os
from datetime import datetime

from ..models.database import db, Edital, Triagem

logger = logging.getLogger(__name__)


def executar_captacao_licitardigital(app_config: dict, periodo_dias: int = 7) -> dict:
    """
    Executa captação completa Licitar Digital → SGL.
    """
    from .licitardigital_scraper import captar_editais_licitardigital

    stats = {
        'plataforma': 'licitardigital',
        'total_encontrados': 0,
        'novos_salvos': 0,
        'duplicados': 0,
        'erros': 0,
    }

    username = os.environ.get('LICITAR_USERNAME') or app_config.get('LICITAR_USERNAME', '')
    password = os.environ.get('LICITAR_PASSWORD') or app_config.get('LICITAR_PASSWORD', '')
    token_manual = os.environ.get('LICITAR_TOKEN') or app_config.get('LICITAR_TOKEN', '')

    if (not username or not password) and not token_manual:
        logger.warning("Licitar Digital: credenciais não configuradas (LICITAR_USERNAME/LICITAR_PASSWORD)")
        stats['erros'] = 1
        stats['erro_msg'] = 'Credenciais Licitar Digital não configuradas'
        return stats

    try:
        resultado = captar_editais_licitardigital(
            username=username,
            password=password,
            dias_recentes=periodo_dias,
            token_manual=token_manual if token_manual else None,
        )

        if not resultado.get('sucesso'):
            erro = resultado.get('erro', 'Erro desconhecido')
            logger.error(f"Licitar Digital captação falhou: {erro}")
            stats['erros'] = 1
            stats['erro_msg'] = erro
            return stats

        editais_sgl = resultado.get('editais', [])
        stats['total_encontrados'] = len(editais_sgl)

        for edital_data in editais_sgl:
            try:
                resultado_save = _salvar_edital_licitardigital(edital_data)
                stats[resultado_save] = stats.get(resultado_save, 0) + 1
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao salvar edital Licitar Digital: {e}")
                stats['erros'] += 1

        logger.info(
            f"Licitar Digital captação concluída: {stats['total_encontrados']} encontrados, "
            f"{stats['novos_salvos']} novos, {stats['duplicados']} duplicados"
        )

    except Exception as e:
        logger.error(f"Erro geral captação Licitar Digital: {e}", exc_info=True)
        stats['erros'] += 1
        stats['erro_msg'] = str(e)

    return stats


def _salvar_edital_licitardigital(edital_data: dict) -> str:
    """Salva edital do Licitar Digital no banco SGL."""
    hash_scraper = edital_data.get('hash_scraper')

    # Dedup por hash
    if hash_scraper:
        existente = Edital.query.filter_by(hash_scraper=hash_scraper).first()
        if existente:
            return 'duplicados'

    # Dedup por processo + orgão + plataforma
    orgao = edital_data.get('orgao_razao_social')
    processo = edital_data.get('numero_processo')
    if orgao and processo:
        existente = Edital.query.filter_by(
            orgao_razao_social=orgao,
            numero_processo=processo,
            plataforma_origem='licitardigital',
        ).first()
        if existente:
            return 'duplicados'

    edital = Edital(
        hash_scraper=hash_scraper,
        numero_pregao=edital_data.get('numero_pregao'),
        numero_processo=edital_data.get('numero_processo'),

        orgao_cnpj=edital_data.get('orgao_cnpj'),
        orgao_razao_social=edital_data.get('orgao_razao_social'),
        unidade_nome=edital_data.get('unidade_nome'),
        uf=edital_data.get('uf'),
        municipio=edital_data.get('municipio'),

        objeto_resumo=edital_data.get('objeto_resumo'),
        objeto_completo=edital_data.get('objeto_completo'),

        modalidade_nome=edital_data.get('modalidade_nome'),
        srp=edital_data.get('srp', False),

        data_publicacao=_parse_data(edital_data.get('data_publicacao')),
        data_abertura_proposta=_parse_data(edital_data.get('data_abertura_proposta')),
        data_encerramento_proposta=_parse_data(edital_data.get('data_encerramento_proposta')),

        plataforma_origem='licitardigital',
        url_original=edital_data.get('url_original'),
        link_sistema_origem=edital_data.get('link_sistema_origem'),

        situacao_pncp=edital_data.get('situacao_pncp'),
        status='captado',
    )

    db.session.add(edital)
    db.session.flush()

    triagem = Triagem(
        edital_id=edital.id,
        decisao='pendente',
        prioridade='media',
    )
    db.session.add(triagem)
    db.session.commit()

    orgao_nome = edital_data.get('orgao_razao_social', 'N/A')
    uf = edital_data.get('uf', '??')
    obj = (edital_data.get('objeto_resumo') or '')[:60]
    logger.info(f"  ✓ Licitar novo: {uf} | {orgao_nome} | {obj}")

    return 'novos_salvos'


def _parse_data(data_str):
    if not data_str:
        return None
    try:
        clean = data_str.replace('Z', '').split('+')[0].split('-03:00')[0]
        return datetime.fromisoformat(clean)
    except (ValueError, TypeError):
        return None
