"""
SGL - Tasks Celery para Captação Automática
Tasks:
  - captacao_automatica: busca periódica no PNCP usando filtros ativos
  - captacao_diaria_completa: busca ampla 1x/dia
  - captacao_manual: disparada pelo frontend (botão Captar)
  - extrair_itens_pendentes: extrai itens via AI dos editais sem extração
  - extrair_itens_edital: extrai itens de 1 edital específico
  - limpeza_logs_antigos: remove logs de atividade antigos
"""
import logging
from datetime import datetime, timedelta, timezone

from sgl.celery_app import celery

logger = logging.getLogger(__name__)


def _get_app_and_service():
    """Helper: cria Flask app e CaptacaoService dentro do contexto."""
    from sgl.app import create_app
    from sgl.services.captacao_service import CaptacaoService

    app = create_app()
    with app.app_context():
        service = CaptacaoService(app.config)
    return app, service


# =============================================================
# CAPTAÇÃO AUTOMÁTICA (agendada pelo Beat)
# =============================================================

@celery.task(
    name='sgl.tasks.captacao_tasks.captacao_automatica',
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
)
def captacao_automatica(self):
    """
    Captação periódica usando filtros ativos.
    Roda a cada 2h no horário comercial (8h, 10h, 12h, 14h, 16h, 18h).
    Busca editais publicados HOJE, aplicando os filtros de prospecção ativos.
    """
    logger.info("=== CAPTAÇÃO AUTOMÁTICA INICIADA ===")

    try:
        from sgl.app import create_app
        from sgl.services.captacao_service import CaptacaoService
        from sgl.models.database import FiltroProspeccao

        app = create_app()
        with app.app_context():
            service = CaptacaoService(app.config)

            # Carregar filtros ativos
            filtros_ativos = FiltroProspeccao.query.filter_by(ativo=True).all()

            if not filtros_ativos:
                logger.info("Nenhum filtro ativo encontrado. Usando padrão (Pregão Eletrônico, todas as UFs).")
                stats = service.executar_captacao(
                    modalidades=[8],
                    ufs=None,
                )
                _registrar_log(app, 'captacao_automatica', stats)
                return stats

            # Coletar UFs e modalidades de todos os filtros
            todas_ufs = set()
            todas_modalidades = set()

            for filtro in filtros_ativos:
                if filtro.regioes_uf:
                    todas_ufs.update(filtro.regioes_uf)
                if filtro.modalidades:
                    todas_modalidades.update(filtro.modalidades)

            ufs = list(todas_ufs) if todas_ufs else None
            modalidades = list(todas_modalidades) if todas_modalidades else [8]

            logger.info(f"Filtros ativos: {len(filtros_ativos)} | UFs: {ufs} | Modalidades: {modalidades}")

            stats = service.executar_captacao(
                modalidades=modalidades,
                ufs=ufs,
                filtros_ids=[f.id for f in filtros_ativos],
            )

            _registrar_log(app, 'captacao_automatica', stats)
            logger.info(f"=== CAPTAÇÃO AUTOMÁTICA CONCLUÍDA: {stats} ===")
            return stats

    except Exception as exc:
        logger.error(f"Erro na captação automática: {exc}")
        raise self.retry(exc=exc)


@celery.task(
    name='sgl.tasks.captacao_tasks.captacao_diaria_completa',
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def captacao_diaria_completa(self):
    """
    Captação ampla 1x por dia (6h da manhã).
    Busca editais publicados ONTEM (para pegar os do fim do dia anterior).
    Usa todas as modalidades e UFs dos filtros ativos.
    """
    logger.info("=== CAPTAÇÃO DIÁRIA COMPLETA INICIADA ===")

    try:
        from sgl.app import create_app
        from sgl.services.captacao_service import CaptacaoService
        from sgl.services.pncp_client import formatar_data_pncp
        from sgl.models.database import FiltroProspeccao

        app = create_app()
        with app.app_context():
            service = CaptacaoService(app.config)

            ontem = datetime.now() - timedelta(days=1)
            data_ontem = formatar_data_pncp(ontem)

            # Carregar filtros ativos
            filtros_ativos = FiltroProspeccao.query.filter_by(ativo=True).all()

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
                data_inicial=data_ontem,
                data_final=data_ontem,
                modalidades=modalidades,
                ufs=ufs,
                filtros_ids=[f.id for f in filtros_ativos] if filtros_ativos else None,
            )

            _registrar_log(app, 'captacao_diaria_completa', stats)
            logger.info(f"=== CAPTAÇÃO DIÁRIA COMPLETA: {stats} ===")
            return stats

    except Exception as exc:
        logger.error(f"Erro na captação diária: {exc}")
        raise self.retry(exc=exc)


# =============================================================
# CAPTAÇÃO MANUAL (disparada pelo frontend)
# =============================================================

@celery.task(
    name='sgl.tasks.captacao_tasks.captacao_manual',
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def captacao_manual(self, modalidades=None, ufs=None, data_inicial=None, data_final=None):
    """
    Captação disparada manualmente pelo usuário via frontend.
    Aceita parâmetros customizados.
    """
    logger.info(f"=== CAPTAÇÃO MANUAL: UFs={ufs}, Mod={modalidades} ===")

    try:
        from sgl.app import create_app
        from sgl.services.captacao_service import CaptacaoService

        app = create_app()
        with app.app_context():
            service = CaptacaoService(app.config)

            stats = service.executar_captacao(
                data_inicial=data_inicial,
                data_final=data_final,
                modalidades=modalidades or [8],
                ufs=ufs,
            )

            _registrar_log(app, 'captacao_manual', stats)
            logger.info(f"=== CAPTAÇÃO MANUAL CONCLUÍDA: {stats} ===")
            return stats

    except Exception as exc:
        logger.error(f"Erro na captação manual: {exc}")
        raise self.retry(exc=exc)


# =============================================================
# EXTRAÇÃO AI DE ITENS
# =============================================================

@celery.task(
    name='sgl.tasks.captacao_tasks.extrair_itens_pendentes',
    bind=True,
    max_retries=2,
)
def extrair_itens_pendentes(self, limite=10):
    """
    Busca editais aprovados que ainda não tiveram itens extraídos via AI.
    Roda a cada 30 min.
    """
    logger.info("=== EXTRAÇÃO AI PENDENTES INICIADA ===")

    try:
        from sgl.app import create_app
        from sgl.services.captacao_service import CaptacaoService
        from sgl.models.database import db, Edital, ItemEditalExtraido
        from sqlalchemy import and_, not_, exists

        app = create_app()
        with app.app_context():
            service = CaptacaoService(app.config)

            if not service.interpreter:
                logger.warning("Claude API não configurada — pulando extração AI")
                return {'msg': 'Claude API não configurada'}

            # Editais aprovados sem itens extraídos
            subquery = db.session.query(ItemEditalExtraido.edital_id).distinct()

            editais_pendentes = Edital.query.filter(
                and_(
                    Edital.status.in_(['aprovado', 'em_processo']),
                    ~Edital.id.in_(subquery)
                )
            ).order_by(Edital.created_at.desc()).limit(limite).all()

            logger.info(f"Encontrados {len(editais_pendentes)} editais sem extração AI")

            resultados = []
            for edital in editais_pendentes:
                try:
                    resultado = service.extrair_itens_edital(edital.id)
                    resultados.append({
                        'edital_id': edital.id,
                        'itens': resultado.get('itens_salvos', 0),
                        'ok': True
                    })
                    logger.info(f"Edital {edital.id}: {resultado.get('itens_salvos', 0)} itens extraídos")
                except Exception as e:
                    resultados.append({
                        'edital_id': edital.id,
                        'erro': str(e),
                        'ok': False
                    })
                    logger.error(f"Erro ao extrair itens do edital {edital.id}: {e}")

            stats = {
                'total_processados': len(resultados),
                'sucesso': sum(1 for r in resultados if r['ok']),
                'erros': sum(1 for r in resultados if not r['ok']),
                'itens_total': sum(r.get('itens', 0) for r in resultados),
            }

            logger.info(f"=== EXTRAÇÃO AI CONCLUÍDA: {stats} ===")
            return stats

    except Exception as exc:
        logger.error(f"Erro na extração AI pendentes: {exc}")
        raise self.retry(exc=exc)


@celery.task(
    name='sgl.tasks.captacao_tasks.extrair_itens_edital',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def extrair_itens_edital(self, edital_id):
    """Extrai itens de um edital específico via Claude AI."""
    logger.info(f"Extraindo itens do edital {edital_id} via AI...")

    try:
        from sgl.app import create_app
        from sgl.services.captacao_service import CaptacaoService

        app = create_app()
        with app.app_context():
            service = CaptacaoService(app.config)
            resultado = service.extrair_itens_edital(edital_id)
            logger.info(f"Edital {edital_id}: {resultado}")
            return resultado

    except Exception as exc:
        logger.error(f"Erro ao extrair itens do edital {edital_id}: {exc}")
        raise self.retry(exc=exc)


# =============================================================
# MANUTENÇÃO
# =============================================================

@celery.task(name='sgl.tasks.captacao_tasks.limpeza_logs_antigos')
def limpeza_logs_antigos(dias=90):
    """Remove logs de atividade mais antigos que X dias."""
    logger.info(f"=== LIMPEZA: removendo logs > {dias} dias ===")

    try:
        from sgl.app import create_app
        from sgl.models.database import db, LogAtividade

        app = create_app()
        with app.app_context():
            limite = datetime.now(timezone.utc) - timedelta(days=dias)
            deletados = LogAtividade.query.filter(
                LogAtividade.created_at < limite
            ).delete()
            db.session.commit()

            logger.info(f"Limpeza concluída: {deletados} logs removidos")
            return {'deletados': deletados}

    except Exception as e:
        logger.error(f"Erro na limpeza: {e}")
        return {'erro': str(e)}


# =============================================================
# HELPERS
# =============================================================

def _registrar_log(app, tipo, stats):
    """Registra atividade de captação no banco."""
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
