import os
from dotenv import load_dotenv
load_dotenv()

"""
SGL - Configuração do Celery
Broker: Redis (localhost:6379/1)
"""
from celery import Celery
from celery.schedules import crontab


def make_celery(app=None):
    """
    Cria instância do Celery integrada ao Flask.
    Pode ser usada com ou sem o app Flask.
    """
    broker = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

    celery = Celery(
        'sgl',
        broker=broker,
        backend=backend,
        include=['sgl.tasks.captacao_tasks', 'sgl.tasks.scraper_tasks']
    )

    celery.conf.update(
        # Serialização
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',

        # Timezone (Brasília)
        timezone='America/Sao_Paulo',
        enable_utc=True,

        # Resultados expiram em 24h
        result_expires=86400,

        # Retry
        task_acks_late=True,
        worker_prefetch_multiplier=1,

        # Limites de tempo por task
        task_soft_time_limit=300,   # 5 min soft
        task_time_limit=600,        # 10 min hard

        # Beat Schedule — Captação automática
        beat_schedule={
            # Captação a cada 2 horas (horário comercial)
            'captacao-periodica': {
                'task': 'sgl.tasks.captacao_tasks.captacao_automatica',
                'schedule': crontab(minute=0, hour='8,10,12,14,16,18'),
                'kwargs': {},
                'options': {'queue': 'captacao'},
            },

            # Captação ampla 1x por dia (6h da manhã - pega tudo da noite anterior)
            'captacao-diaria-completa': {
                'task': 'sgl.tasks.captacao_tasks.captacao_diaria_completa',
                'schedule': crontab(minute=0, hour=6),
                'kwargs': {},
                'options': {'queue': 'captacao'},
            },

            # Extração AI de itens pendentes a cada 30 min
            'extracao-ai-pendentes': {
                'task': 'sgl.tasks.captacao_tasks.extrair_itens_pendentes',
                'schedule': crontab(minute='*/30'),
                'kwargs': {},
                'options': {'queue': 'ai'},
            },

            # Scraping BLL + BNC + Licitanet (3x/dia)
            'scraping-periodico': {
                'task': 'sgl.tasks.scraper_tasks.scraping_automatico',
                'schedule': crontab(minute=30, hour='9,13,17'),
                'kwargs': {},
                'options': {'queue': 'scraping'},
            },

            # Limpeza de logs antigos (1x por semana, domingo 3h)
            'limpeza-semanal': {
                'task': 'sgl.tasks.captacao_tasks.limpeza_logs_antigos',
                'schedule': crontab(minute=0, hour=3, day_of_week='sunday'),
                'kwargs': {'dias': 90},
                'options': {'queue': 'default'},
            },
        },

        # Filas
        task_routes={
            'sgl.tasks.captacao_tasks.captacao_*': {'queue': 'captacao'},
            'sgl.tasks.captacao_tasks.extrair_*': {'queue': 'ai'},
            'sgl.tasks.captacao_tasks.limpeza_*': {'queue': 'default'},
            'sgl.tasks.scraper_tasks.*': {'queue': 'scraping'},
        },
    )

    # Integrar com Flask (se app fornecido)
    if app:
        celery.conf.update(app.config)

        class ContextTask(celery.Task):
            """Garante que tasks rodem dentro do contexto do Flask."""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery


# Instância global (usada pelo worker e beat)
celery = make_celery()
