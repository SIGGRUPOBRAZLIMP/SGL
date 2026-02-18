"""
Script para integrar Licitar Digital ao SGL.
Atualiza: routes.py (endpoint unificado), scheduler.py, frontend.
"""
import os

BASE = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES'

# ============================================================
# 1. PATCH routes.py — adicionar Licitar Digital ao endpoint unificado
# ============================================================
routes_path = os.path.join(BASE, 'sgl', 'api', 'routes.py')
content = open(routes_path, 'r', encoding='utf-8').read()

# Encontrar o bloco BBMNET e adicionar Licitar Digital após ele
old_block = """    # Combinar resultados
    resultado_pncp['bbmnet'] = resultado_bbmnet
    resultado_pncp['total_geral'] = (
        resultado_pncp.get('novos_salvos', 0) +
        resultado_bbmnet.get('novos_salvos', 0)
    )
    return jsonify(resultado_pncp)"""

new_block = """    # LICITAR DIGITAL - captar tambem
    resultado_licitar = {}
    try:
        from ..services.licitardigital_integration import executar_captacao_licitardigital as captar_licitar
        resultado_licitar = captar_licitar(
            app_config=current_app.config,
            periodo_dias=periodo,
        )
    except Exception as e:
        resultado_licitar = {'erro': str(e)}

    # Combinar resultados
    resultado_pncp['bbmnet'] = resultado_bbmnet
    resultado_pncp['licitardigital'] = resultado_licitar
    resultado_pncp['total_geral'] = (
        resultado_pncp.get('novos_salvos', 0) +
        resultado_bbmnet.get('novos_salvos', 0) +
        resultado_licitar.get('novos_salvos', 0)
    )
    return jsonify(resultado_pncp)"""

if old_block in content:
    content = content.replace(old_block, new_block)
    open(routes_path, 'w', encoding='utf-8').write(content)
    print('OK - routes.py atualizado com Licitar Digital')
else:
    print('AVISO - bloco BBMNET não encontrado no routes.py, verifique manualmente')

# ============================================================
# 2. PATCH scheduler.py — adicionar jobs Licitar Digital
# ============================================================
scheduler_path = os.path.join(BASE, 'sgl', 'scheduler.py')
content = open(scheduler_path, 'r', encoding='utf-8').read()

# Adicionar job Licitar Digital após o BBMNET semanal
old_scheduler = """    logger.info(f"Jobs registrados: {[j.id for j in scheduler.get_jobs()]}")"""

new_scheduler = """    # ----------------------------------------------------------
    # 6. Captacao LICITAR DIGITAL — 2x/dia as 8h e 14h
    # ----------------------------------------------------------
    scheduler.add_job(
        func=_job_captacao_licitardigital,
        trigger=CronTrigger(hour='8,14', minute=0),
        id='captacao_licitardigital',
        name='Captacao Licitar Digital (2x/dia)',
        kwargs={'app': app, 'periodo_dias': 3},
        replace_existing=True,
    )

    # ----------------------------------------------------------
    # 7. Captacao LICITAR DIGITAL retroativa — domingo 5h30
    # ----------------------------------------------------------
    scheduler.add_job(
        func=_job_captacao_licitardigital,
        trigger=CronTrigger(day_of_week='sun', hour=5, minute=30),
        id='captacao_licitardigital_semanal',
        name='Captacao retroativa semanal Licitar Digital (7 dias)',
        kwargs={'app': app, 'periodo_dias': 7},
        replace_existing=True,
    )

    logger.info(f"Jobs registrados: {[j.id for j in scheduler.get_jobs()]}")"""

if old_scheduler in content:
    content = content.replace(old_scheduler, new_scheduler)

# Adicionar a função do job
old_job_end = """            return {'erro': str(e)}"""
# Encontrar o último return erro (do bbmnet)
# Vamos adicionar a função no final do arquivo
job_function = '''


def _job_captacao_licitardigital(app, periodo_dias=3):
    """
    Executa captacao automatica Licitar Digital dentro do contexto Flask.
    """
    with app.app_context():
        try:
            from .services.licitardigital_integration import executar_captacao_licitardigital
            from .models.database import db, LogAtividade

            logger.info(f"=== CAPTACAO LICITAR DIGITAL AUTOMATICA | periodo: {periodo_dias} dias ===")

            stats = executar_captacao_licitardigital(
                app_config=app.config,
                periodo_dias=periodo_dias,
            )

            # Registrar log
            try:
                log = LogAtividade(
                    acao='captacao_licitardigital',
                    entidade='edital',
                    detalhes={
                        'stats': stats,
                        'periodo_dias': periodo_dias,
                    },
                )
                db.session.add(log)
                db.session.commit()
            except Exception as e:
                logger.warning(f"Erro ao registrar log Licitar Digital: {e}")

            logger.info(f"=== CAPTACAO LICITAR DIGITAL CONCLUIDA: {stats} ===")
            return stats

        except Exception as e:
            logger.error(f"Erro na captacao Licitar Digital automatica: {e}", exc_info=True)
            return {'erro': str(e)}
'''

# Append job function at end of file
if '_job_captacao_licitardigital' not in content:
    content = content.rstrip() + job_function

open(scheduler_path, 'w', encoding='utf-8').write(content)
print('OK - scheduler.py atualizado com Licitar Digital')

# ============================================================
# 3. PATCH Captacao.jsx — adicionar stats Licitar Digital
# ============================================================
jsx_path = os.path.join(BASE, 'sgl-frontend', 'src', 'pages', 'Captacao.jsx')
content = open(jsx_path, 'r', encoding='utf-8').read()

# Atualizar subtitulo
content = content.replace(
    'PNCP e BBMNET (multi-plataforma',
    'PNCP, BBMNET e Licitar Digital (multi-plataforma'
)

# Atualizar texto loading
content = content.replace(
    'Captando editais PNCP + BBMNET',
    'Captando editais PNCP + BBMNET + Licitar'
)

# Adicionar bloco Licitar Digital no resultado
old_bbmnet_block = """              )}
            </div>
          )}"""

# Encontrar o bloco BBMNET e adicionar Licitar Digital depois
# Mais seguro: adicionar após o fechamento do bloco bbmnet
licitar_block = """              )}
            </div>
          )}

          {/* Resultados Licitar Digital */}
          {result.licitardigital && (
            <div className="mt-4 p-3 bg-white bg-opacity-60 rounded-lg">
              <h4 className="text-sm font-semibold text-purple-700 mb-2">Licitar Digital</h4>
              <div className="grid grid-cols-3 gap-4">
                <ResultStat label="Encontrados" value={result.licitardigital.total_encontrados || 0} />
                <ResultStat label="Novos salvos" value={result.licitardigital.novos_salvos || 0} highlight />
                <ResultStat label="Duplicados" value={result.licitardigital.duplicados || 0} />
              </div>
              {result.licitardigital.erro_msg && (
                <p className="text-xs text-red-500 mt-1">{result.licitardigital.erro_msg}</p>
              )}
            </div>
          )}"""

# Replace only the FIRST occurrence of the bbmnet closing block
if old_bbmnet_block in content:
    # Find position after bbmnet block
    idx = content.find(old_bbmnet_block)
    if idx >= 0:
        content = content[:idx] + licitar_block + content[idx + len(old_bbmnet_block):]

open(jsx_path, 'w', encoding='utf-8').write(content)
print('OK - Captacao.jsx atualizado com Licitar Digital')

# ============================================================
# 4. PATCH Dashboard.jsx
# ============================================================
dash_path = os.path.join(BASE, 'sgl-frontend', 'src', 'pages', 'Dashboard.jsx')
content = open(dash_path, 'r', encoding='utf-8').read()
content = content.replace('PNCP e BBMNET', 'PNCP, BBMNET e Licitar Digital')
open(dash_path, 'w', encoding='utf-8').write(content)
print('OK - Dashboard.jsx atualizado')

print('\n=== TODAS AS ATUALIZACOES CONCLUIDAS ===')
print('Proximo: copiar scraper e integration para sgl/services/')
