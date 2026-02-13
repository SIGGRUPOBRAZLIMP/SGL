"""
SGL - Script de gerenciamento do Celery
Uso:
    python -m sgl.tasks.manage status       → Verificar conexão com Redis
    python -m sgl.tasks.manage captar       → Disparar captação manual
    python -m sgl.tasks.manage extrair 5    → Extrair itens AI de 5 editais
    python -m sgl.tasks.manage agendar      → Listar agendamentos do Beat
"""
import sys
import os

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()


def check_redis():
    """Verifica conexão com Redis."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=1)
        r.ping()
        print("✅ Redis: conectado (localhost:6379)")
        info = r.info('server')
        print(f"   Versão: {info.get('redis_version', '?')}")
        return True
    except Exception as e:
        print(f"❌ Redis: erro - {e}")
        return False


def check_celery():
    """Verifica se o Celery está configurado."""
    try:
        from sgl.celery_app import celery
        print(f"✅ Celery: configurado")
        print(f"   Broker: {celery.conf.broker_url}")
        print(f"   Backend: {celery.conf.result_backend}")
        return True
    except Exception as e:
        print(f"❌ Celery: {e}")
        return False


def show_schedule():
    """Mostra os agendamentos do Beat."""
    from sgl.celery_app import celery
    print("\n📅 Agendamentos do Celery Beat:")
    print("-" * 60)
    for name, entry in celery.conf.beat_schedule.items():
        print(f"\n  📌 {name}")
        print(f"     Task: {entry['task']}")
        print(f"     Schedule: {entry['schedule']}")
        if entry.get('options', {}).get('queue'):
            print(f"     Fila: {entry['options']['queue']}")
    print()


def run_captacao_manual():
    """Dispara captação manual via Celery."""
    from sgl.tasks.captacao_tasks import captacao_manual
    print("🚀 Disparando captação manual via Celery...")
    result = captacao_manual.delay(modalidades=[8], ufs=['RJ', 'SP', 'MG', 'ES'])
    print(f"   Task ID: {result.id}")
    print(f"   Status: {result.status}")
    print(f"   Aguardando resultado (timeout 120s)...")

    try:
        stats = result.get(timeout=120)
        print(f"\n✅ Resultado: {stats}")
    except Exception as e:
        print(f"\n⚠️  Timeout ou erro: {e}")
        print("   (O worker está rodando? Abra outro terminal e execute o worker)")


def run_captacao_sincrona():
    """Executa captação SEM Celery (síncrono, para teste)."""
    from sgl.app import create_app
    from sgl.services.captacao_service import CaptacaoService

    print("🔄 Executando captação SÍNCRONA (sem Celery)...")
    app = create_app()
    with app.app_context():
        service = CaptacaoService(app.config)
        stats = service.executar_captacao(
            modalidades=[8],
            ufs=['RJ', 'SP', 'MG', 'ES']
        )
        print(f"\n✅ Resultado: {stats}")


def run_extracao(limite=5):
    """Dispara extração AI pendentes."""
    from sgl.tasks.captacao_tasks import extrair_itens_pendentes
    print(f"🧠 Disparando extração AI (limite={limite})...")
    result = extrair_itens_pendentes.delay(limite=limite)
    print(f"   Task ID: {result.id}")

    try:
        stats = result.get(timeout=300)
        print(f"\n✅ Resultado: {stats}")
    except Exception as e:
        print(f"\n⚠️  {e}")


if __name__ == '__main__':
    args = sys.argv[1:]
    comando = args[0] if args else 'status'

    print("=" * 50)
    print("  SGL — Gerenciamento Celery")
    print("=" * 50)

    if comando == 'status':
        check_redis()
        check_celery()
        show_schedule()

    elif comando == 'captar':
        check_redis()
        run_captacao_manual()

    elif comando == 'captar-sync':
        run_captacao_sincrona()

    elif comando == 'extrair':
        limite = int(args[1]) if len(args) > 1 else 5
        run_extracao(limite)

    elif comando == 'agendar':
        show_schedule()

    else:
        print(f"Comando desconhecido: {comando}")
        print("Comandos: status, captar, captar-sync, extrair [N], agendar")
