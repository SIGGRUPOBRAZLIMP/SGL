"""
SGL - Integração BBMNET → Banco de dados SGL
Camada entre o scraper BBMNET e o modelo Edital do SGL.
"""
import logging
import os
from datetime import datetime, timezone

from ..models.database import db, Edital, Triagem

logger = logging.getLogger(__name__)


def executar_captacao_bbmnet(app_config: dict, periodo_dias: int = 7, ufs: list = None) -> dict:
    """
    Executa captação completa BBMNET → SGL.
    
    Args:
        app_config: Flask app.config
        periodo_dias: Buscar últimos N dias
        ufs: Lista de UFs (padrão: RJ, SP, MG, ES)
    
    Returns:
        dict com estatísticas da captação
    """
    from .bbmnet_scraper import captar_editais_bbmnet
    
    stats = {
        'plataforma': 'bbmnet',
        'total_encontrados': 0,
        'novos_salvos': 0,
        'duplicados': 0,
        'erros': 0,
        'detalhes_uf': {},
    }
    
    # Credenciais via env vars ou config
    username = os.environ.get('BBMNET_USERNAME') or app_config.get('BBMNET_USERNAME', '')
    password = os.environ.get('BBMNET_PASSWORD') or app_config.get('BBMNET_PASSWORD', '')
    
    if not username or not password:
        logger.warning("BBMNET: credenciais não configuradas (BBMNET_USERNAME / BBMNET_PASSWORD)")
        stats['erros'] = 1
        stats['erro_msg'] = 'Credenciais BBMNET não configuradas'
        return stats
    
    if ufs is None:
        ufs = ['RJ', 'SP', 'MG', 'ES']
    
    try:
        resultado = captar_editais_bbmnet(
            username=username,
            password=password,
            ufs=ufs,
            modalidade_id=3,  # Pregão Setor Público
            dias_recentes=periodo_dias,
        )
        
        if not resultado.get('sucesso'):
            erro = resultado.get('erro', 'Erro desconhecido')
            logger.error(f"BBMNET captação falhou: {erro}")
            stats['erros'] = 1
            stats['erro_msg'] = erro
            return stats
        
        editais_sgl = resultado.get('editais', [])
        stats['total_encontrados'] = len(editais_sgl)
        stats['detalhes_uf'] = resultado.get('stats', {}).get('por_uf', {})
        
        # Salvar cada edital no banco
        for edital_data in editais_sgl:
            try:
                resultado_save = _salvar_edital_bbmnet(edital_data)
                stats[resultado_save] = stats.get(resultado_save, 0) + 1
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erro ao salvar edital BBMNET: {e}")
                stats['erros'] += 1
        
        logger.info(
            f"BBMNET captação concluída: {stats['total_encontrados']} encontrados, "
            f"{stats['novos_salvos']} novos, {stats['duplicados']} duplicados, "
            f"{stats['erros']} erros"
        )
        
    except Exception as e:
        logger.error(f"Erro geral na captação BBMNET: {e}", exc_info=True)
        stats['erros'] += 1
        stats['erro_msg'] = str(e)
    
    return stats


def _salvar_edital_bbmnet(edital_data: dict) -> str:
    """
    Salva um edital do BBMNET no banco SGL.
    Deduplicação via hash_scraper.
    
    Returns:
        'novos_salvos', 'duplicados' ou 'erros'
    """
    hash_scraper = edital_data.get('hash_scraper')
    
    # Verificar duplicidade por hash
    if hash_scraper:
        existente = Edital.query.filter_by(hash_scraper=hash_scraper).first()
        if existente:
            return 'duplicados'
    
    # Verificar duplicidade por CNPJ + número processo (safety net)
    cnpj = edital_data.get('orgao_cnpj')
    processo = edital_data.get('numero_processo')
    if cnpj and processo:
        existente = Edital.query.filter_by(
            orgao_cnpj=cnpj,
            numero_processo=processo,
            plataforma_origem='bbmnet',
        ).first()
        if existente:
            return 'duplicados'
    
    # Criar edital
    edital = Edital(
        numero_controle_pncp=None,
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
        
        plataforma_origem='bbmnet',
        url_original=edital_data.get('url_original'),
        link_sistema_origem=edital_data.get('link_sistema_origem'),
        
        situacao_pncp=edital_data.get('situacao_pncp'),
        status='captado',
    )
    
    db.session.add(edital)
    db.session.flush()
    
    # Criar triagem pendente
    triagem = Triagem(
        edital_id=edital.id,
        decisao='pendente',
        prioridade='media',
    )
    db.session.add(triagem)
    db.session.commit()
    
    orgao = edital_data.get('orgao_razao_social', 'N/A')
    uf = edital_data.get('uf', '??')
    obj = (edital_data.get('objeto_resumo') or '')[:60]
    logger.info(f"  ✓ BBMNET novo: {uf} | {orgao} | {obj}")
    
    return 'novos_salvos'


def _parse_data(data_str: str):
    """Parse de data ISO."""
    if not data_str:
        return None
    try:
        # Remover timezone info para simplificar
        clean = data_str.split('+')[0].split('-03:00')[0].replace('Z', '')
        return datetime.fromisoformat(clean)
    except (ValueError, TypeError):
        return None
