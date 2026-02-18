import { useState } from 'react'
import { captarEditais } from '../services/api'
import { Search, RefreshCw, CheckCircle, MapPin, Calendar, AlertTriangle } from 'lucide-react'

const UFS = ['AC','AL','AM','AP','BA','CE','DF','ES','GO','MA','MG','MS','MT','PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO']
const MODALIDADES = [
  { id: 8, nome: 'Pregão Eletrônico' },
  { id: 6, nome: 'Pregão Presencial' },
  { id: 1, nome: 'Leilão Eletrônico' },
  { id: 2, nome: 'Diálogo Competitivo' },
  { id: 3, nome: 'Concurso' },
  { id: 4, nome: 'Concorrência Eletrônica' },
  { id: 5, nome: 'Concorrência Presencial' },
  { id: 7, nome: 'Dispensa de Licitação' },
  { id: 9, nome: 'Leilão Presencial' },
  { id: 12, nome: 'Credenciamento' },
  { id: 13, nome: 'Pré-qualificação' },
]
const PERIODOS = [
  { dias: 1, nome: 'Hoje' },
  { dias: 3, nome: 'Últimos 3 dias' },
  { dias: 7, nome: 'Última semana' },
  { dias: 15, nome: 'Últimos 15 dias' },
  { dias: 30, nome: 'Último mês' },
]

export default function Captacao() {
  const [ufs, setUfs] = useState(['RJ', 'MG', 'SP', 'ES'])
  const [modalidades, setModalidades] = useState([8])
  const [periodoDias, setPeriodoDias] = useState(3)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const toggleUf = (uf) => {
    setUfs(prev => prev.includes(uf) ? prev.filter(u => u !== uf) : [...prev, uf])
  }

  const toggleModalidade = (id) => {
    setModalidades(prev => prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id])
  }

  const handleCaptar = async () => {
    if (ufs.length === 0) { setError('Selecione pelo menos uma UF'); return }
    if (modalidades.length === 0) { setError('Selecione pelo menos uma modalidade'); return }

    setLoading(true)
    setResult(null)
    setError('')
    try {
      const r = await captarEditais({ modalidades, ufs, periodo_dias: periodoDias })
      setResult(r.data)
    } catch (err) {
      setError(err.response?.data?.error || 'Erro na captação')
    } finally {
      setLoading(false)
    }
  }

  const selectAllUfs = () => setUfs([...UFS])
  const selectSudeste = () => setUfs(['RJ', 'SP', 'MG', 'ES'])
  const clearUfs = () => setUfs([])

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Captação de Editais</h1>
        <p className="text-gray-500">Buscar novos editais no PNCP, BBMNET e Licitar Digital (multi-plataformações Públicas)</p>
      </div>

      {/* Período */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <Calendar size={18} /> Período de Busca
        </h2>
        <div className="flex flex-wrap gap-2">
          {PERIODOS.map(p => (
            <button
              key={p.dias}
              onClick={() => setPeriodoDias(p.dias)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                periodoDias === p.dias
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {p.nome}
            </button>
          ))}
        </div>
        <p className="text-sm text-gray-400 mt-2">
          Buscar editais publicados nos últimos {periodoDias} dia(s).
          Quanto maior o período, mais editais serão verificados (duplicados são ignorados automaticamente).
        </p>
      </div>

      {/* Modalidades */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Modalidades</h2>
        <div className="flex flex-wrap gap-2">
          {MODALIDADES.map(m => (
            <button
              key={m.id}
              onClick={() => toggleModalidade(m.id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                modalidades.includes(m.id) ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {m.nome}
            </button>
          ))}
        </div>
      </div>

      {/* UFs */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <MapPin size={18} /> Estados (UF)
          </h2>
          <div className="flex gap-2">
            <button onClick={selectSudeste} className="text-xs btn-secondary py-1 px-2">Sudeste</button>
            <button onClick={selectAllUfs} className="text-xs btn-secondary py-1 px-2">Todos</button>
            <button onClick={clearUfs} className="text-xs btn-secondary py-1 px-2">Limpar</button>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {UFS.map(uf => (
            <button
              key={uf}
              onClick={() => toggleUf(uf)}
              className={`w-11 h-9 rounded-lg text-sm font-medium transition-colors ${
                ufs.includes(uf) ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {uf}
            </button>
          ))}
        </div>
        {ufs.length > 0 && (
          <p className="text-sm text-gray-400 mt-2">{ufs.length} estado(s) selecionado(s): {ufs.join(', ')}</p>
        )}
      </div>

      {/* Botão Captar */}
      <div className="card mb-6">
        <button
          onClick={handleCaptar}
          disabled={loading}
          className="btn-primary w-full py-4 text-lg flex items-center justify-center gap-3 disabled:opacity-50"
        >
          {loading ? (
            <>
              <RefreshCw size={22} className="animate-spin" />
              Captando editais PNCP + BBMNET + Licitar ({periodoDias} dias)...
            </>
          ) : (
            <>
              <Search size={22} />
              Captar Editais Agora — últimos {periodoDias} dia(s)
            </>
          )}
        </button>
      </div>

      {/* Erro */}
      {error && (
        <div className="p-4 bg-danger-50 text-danger-700 rounded-lg mb-4 flex items-center gap-2">
          <AlertTriangle size={18} />
          {error}
        </div>
      )}

      {/* Resultado */}
      {result && (
        <div className="card bg-success-50 border-success-500">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle size={24} className="text-success-500" />
            <h3 className="text-lg font-semibold text-success-700">Captação Concluída!</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <ResultStat label="PNCP encontrados" value={result.total_encontrados} />
            <ResultStat label="Novos salvos" value={result.novos_salvos} highlight />
            <ResultStat label="Já existiam (duplicados)" value={result.duplicados} />
            <ResultStat label="Filtrados" value={result.filtrados} />
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
          )}

          {/* Detalhes por UF */}
          {result.detalhes_uf && Object.keys(result.detalhes_uf).length > 0 && (
            <div className="mt-4 border-t border-success-200 pt-4">
              <h4 className="text-sm font-semibold text-success-700 mb-2">Detalhes por Estado</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {Object.entries(result.detalhes_uf).map(([uf, stats]) => (
                  <div key={uf} className="bg-white bg-opacity-60 rounded px-3 py-2 text-sm">
                    <span className="font-semibold text-gray-700">{uf}:</span>{' '}
                    <span className="text-gray-600">
                      {stats.encontrados} encontrados, {stats.novos_salvos} novos, {stats.duplicados} duplicados
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Período */}
          {result.periodo && (
            <p className="text-xs text-success-600 mt-3">
              Período: {result.periodo.data_inicial} → {result.periodo.data_final}
              {result.periodo.periodo_dias && ` (${result.periodo.periodo_dias} dias)`}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function ResultStat({ label, value, highlight }) {
  return (
    <div className="text-center">
      <p className={`text-3xl font-bold ${highlight ? 'text-success-700' : 'text-gray-700'}`}>{value}</p>
      <p className="text-sm text-gray-500">{label}</p>
    </div>
  )
}
