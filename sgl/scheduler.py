"""
SGL - Agendador de tarefas (substitui Celery Beat + Worker)
Usa APScheduler para rodar dentro do próprio Flask — sem Redis.
"""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(
    timezone='America/Sao_Paulo',
    job_defaults={
        'coalesce': True,          # Se perdeu execuções, roda só 1
        'max_instances': 1,         # Nunca roda 2 instâncias da mesma task
        'misfire_grace_time': 3600, # 1h de tolerância para execuções atrasadas
    },
)


def init_scheduler(app):
    """
    Inicializa o scheduler dentro do contexto do Flask.
    Chamado uma única vez na criação do app.
    """
    # Evitar dupla inicialização (gunicorn com múltiplos workers)
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        _registrar_jobs(app)
        scheduler.start()
        logger.info("=== APScheduler iniciado com sucesso ===")
    else:
        logger.info("APScheduler: aguardando reloader (debug mode)")


def _registrar_jobs(app):
    """Registra todos os jobs agendados."""

    # ----------------------------------------------------------
    # 1. Captação automática — a cada 2h no horário comercial
    # ----------------------------------------------------------
    scheduler.add_job(
        func=_job_captacao_automatica,
        trigger=CronTrigger(hour='8,10,12,14,16,18', minute=0),
        id='captacao_automatica',
        name='Captação automática PNCP (2h em 2h)',
        kwargs={'app': app, 'periodo_dias': 3},
        replace_existing=True,
    )

    # ----------------------------------------------------------
    # 2. Captação retroativa — 1x/dia às 6h (últimos 3 dias)
    # ----------------------------------------------------------
    scheduler.add_job(
        func=_job_captacao_automatica,
        trigger=CronTrigger(hour=6, minute=0),
        id='captacao_diaria',
        name='Captação diária completa (3 dias)',
        kwargs={'app': app, 'periodo_dias': 3},
        replace_existing=True,
    )

    # ----------------------------------------------------------
    # 3. Captação retroativa semanal — domingo 4h (últimos 7 dias)
    # ----------------------------------------------------------
    scheduler.add_job(
        func=_job_captacao_automatica,
        trigger=CronTrigger(day_of_week='sun', hour=4, minute=0),
        id='captacao_semanal',
        name='Captação retroativa semanal (7 dias)',
        kwargs={'app': app, 'periodo_dias': 7},
        replace_existing=True,
    )

    logger.info(f"Jobs registrados: {[j.id for j in scheduler.get_jobs()]}")


# ==============================================================
# FUNÇÕES DOS JOBS
# ==============================================================

def _job_captacao_automatica(app, periodo_dias=3):
    """
    Executa captação automática dentro do contexto Flask.
    """
    with app.app_context():
        try:
            from .services.captacao_service import CaptacaoService
            from .models.database import FiltroProspeccao, db, LogAtividade

            logger.info(f"=== CAPTAÇÃO AUTOMÁTICA | período: {periodo_dias} dias ===")

            service = CaptacaoService(app.config)

            # Carregar filtros ativos
            filtros_ativos = FiltroProspeccao.query.filter_by(ativo=True).all()

            ufs = None
            modalidades = [8]  # Pregão Eletrônico por padrão

            if filtros_ativos:
                todas_ufs = set()
                todas_modalidades = set()
                for filtro in filtros_ativos:
                    if filtro.regioes_uf:
                        todas_ufs.update(filtro.regioes_uf)
                    if filtro.modalidades:
                        todas_modalidades.update(filtro.modalidades)
                ufs = list(todas_ufs) if todas_ufs else None
                modalidades = list(todas_modalidades) if todas_modalidades else [8]

            stats = service.executar_captacao(
                periodo_dias=periodo_dias,
                modalidades=modalidades,
                ufs=ufs,
                filtros_ids=[f.id for f in filtros_ativos] if filtros_ativos else None,
            )

            # Registrar log
            try:
                log = LogAtividade(
                    acao='captacao_automatica',
                    entidade='edital',
                    detalhes={
                        'stats': stats,
                        'periodo_dias': periodo_dias,
                        'ufs': ufs,
                        'modalidades': modalidades,
                    },
                )
                db.session.add(log)
                db.session.commit()
            except Exception as e:
                logger.warning(f"Erro ao registrar log: {e}")

            logger.info(f"=== CAPTAÇÃO AUTOMÁTICA CONCLUÍDA: {stats} ===")
            return stats

        except Exception as e:
            logger.error(f"Erro na captação automática: {e}", exc_info=True)
            return {'erro': str(e)}
