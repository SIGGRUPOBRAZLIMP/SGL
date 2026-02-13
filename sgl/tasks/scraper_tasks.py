"""
SGL - Tasks Celery para Scrapers
Tasks:
  - scraping_automatico: scraping periódico BLL + BNC + Licitanet
  - scraping_plataforma: scraping de uma plataforma específica
  - scraping_manual: disparado pelo frontend
"""
import logging
from sgl.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(
    name='sgl.tasks.scraper_tasks.scraping_automatico',
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def scraping_automatico(self, plataformas=None):
    """
    Scraping automático de todas as plataformas.
    Roda a cada 3 horas no horário comercial (9h, 12h, 15h, 18h).
    """
    logger.info("=== SCRAPING AUTOMÁTICO INICIADO ===")

    try:
        from sgl.app import create_app
        from sgl.services.scraper_service import ScraperService
        from sgl.models.database import FiltroProspeccao

        app = create_app()
        with app.app_context():
            # Carregar filtros ativos para pegar termos de busca
            filtros = FiltroProspeccao.query.filter_by(ativo=True).all()

            service = ScraperService(plataformas=plataformas)

            stats_total = {
                'total_encontrados': 0,
                'novos_salvos': 0,
                'duplicados': 0,
                'erros': 0,
                'por_filtro': [],
            }

            if filtros:
                # Executar scraping para cada filtro (termos de busca)
                for filtro in filtros:
                    termos = filtro.palavras_chave or []
                    ufs = filtro.regioes_uf or [None]

                    for termo in (termos or [None]):
                        for uf in ufs[:3]:  # Limitar UFs por filtro
                            try:
                                stats = service.executar_scraping(
                                    termo=termo,
                                    uf=uf,
                                    max_paginas=2,
                                )
                                stats_total['total_encontrados'] += stats['total_encontrados']
                                stats_total['novos_salvos'] += stats['novos_salvos']
                                stats_total['duplicados'] += stats['duplicados']
                                stats_total['erros'] += stats['erros']
                            except Exception as e:
                                logger.error(f"Erro scraping termo={termo} uf={uf}: {e}")
                                stats_total['erros'] += 1
            else:
                # Sem filtros: busca geral
                stats = service.executar_scraping(max_paginas=3)
                stats_total['total_encontrados'] = stats['total_encontrados']
                stats_total['novos_salvos'] = stats['novos_salvos']
                stats_total['duplicados'] = stats['duplicados']
                stats_total['erros'] = stats['erros']

            # Registrar log
            _registrar_log(app, 'scraping_automatico', stats_total)

            logger.info(f"=== SCRAPING AUTOMÁTICO CONCLUÍDO: {stats_total} ===")
            return stats_total

    except Exception as exc:
        logger.error(f"Erro no scraping automático: {exc}")
        raise self.retry(exc=exc)


@celery.task(
    name='sgl.tasks.scraper_tasks.scraping_plataforma',
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def scraping_plataforma(self, plataforma, termo=None, uf=None, max_paginas=3):
    """Scraping de uma plataforma específica."""
    logger.info(f"=== SCRAPING {plataforma.upper()} ===")

    try:
        from sgl.app import create_app
        from sgl.services.scraper_service import ScraperService

        app = create_app()
        with app.app_context():
            service = ScraperService(plataformas=[plataforma])
            stats = service.executar_scraping(
                termo=termo,
                uf=uf,
                max_paginas=max_paginas,
            )
            logger.info(f"=== {plataforma.upper()} CONCLUÍDO: {stats} ===")
            return stats

    except Exception as exc:
        logger.error(f"Erro scraping {plataforma}: {exc}")
        raise self.retry(exc=exc)


@celery.task(
    name='sgl.tasks.scraper_tasks.scraping_manual',
    bind=True,
    max_retries=1,
    default_retry_delay=30,
)
def scraping_manual(self, plataformas=None, termo=None, uf=None, max_paginas=3):
    """Scraping manual disparado pelo frontend."""
    plats = plataformas or ['bll', 'bnc', 'licitanet']
    logger.info(f"=== SCRAPING MANUAL: {plats} | termo={termo} | uf={uf} ===")

    try:
        from sgl.app import create_app
        from sgl.services.scraper_service import ScraperService

        app = create_app()
        with app.app_context():
            service = ScraperService(plataformas=plats)
            stats = service.executar_scraping(
                termo=termo,
                uf=uf,
                max_paginas=max_paginas,
            )
            _registrar_log(app, 'scraping_manual', stats)
            logger.info(f"=== SCRAPING MANUAL CONCLUÍDO: {stats} ===")
            return stats

    except Exception as exc:
        logger.error(f"Erro scraping manual: {exc}")
        raise self.retry(exc=exc)


def _registrar_log(app, tipo, stats):
    """Registra atividade no banco."""
    try:
        from sgl.models.database import db, LogAtividade

        with app.app_context():
            log = LogAtividade(
                acao=tipo,
                entidade='edital',
                detalhes={
                    'stats': stats,
                    'novos': stats.get('novos_salvos', 0),
                    'duplicados': stats.get('duplicados', 0),
                },
            )
            db.session.add(log)
            db.session.commit()
    except Exception as e:
        logger.warning(f"Erro ao registrar log: {e}")
