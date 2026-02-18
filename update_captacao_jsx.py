"""Script para atualizar Captacao.jsx com suporte multi-plataforma"""
import sys

path = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl-frontend\src\pages\Captacao.jsx'
content = open(path, 'r', encoding='utf-8').read()

# 1. Subtitulo
content = content.replace(
    'Buscar novos editais no PNCP (Portal Nacional de Contrata',
    'Buscar novos editais no PNCP e BBMNET (multi-plataforma'
)

# 2. Texto loading
content = content.replace(
    'Captando editais do PNCP ({periodoDias} dias)...',
    'Captando editais PNCP + BBMNET ({periodoDias} dias)...'
)

# 3. Label resultado
content = content.replace(
    'Encontrados no PNCP',
    'PNCP encontrados'
)

# 4. Adicionar stats BBMNET no resultado
old_stats = '            <ResultStat label="Filtrados" value={result.filtrados} />\n          </div>'

new_stats = """            <ResultStat label="Filtrados" value={result.filtrados} />
          </div>

          {/* Resultados BBMNET */}
          {result.bbmnet && (
            <div className="mt-4 p-3 bg-white bg-opacity-60 rounded-lg">
              <h4 className="text-sm font-semibold text-blue-700 mb-2">BBMNET</h4>
              <div className="grid grid-cols-3 gap-4">
                <ResultStat label="Encontrados" value={result.bbmnet.total_encontrados || 0} />
                <ResultStat label="Novos salvos" value={result.bbmnet.novos_salvos || 0} highlight />
                <ResultStat label="Duplicados" value={result.bbmnet.duplicados || 0} />
              </div>
              {result.bbmnet.erro && (
                <p className="text-xs text-red-500 mt-1">{result.bbmnet.erro}</p>
              )}
            </div>
          )}"""

content = content.replace(old_stats, new_stats)

open(path, 'w', encoding='utf-8').write(content)
print('OK - Captacao.jsx atualizado com suporte BBMNET')
