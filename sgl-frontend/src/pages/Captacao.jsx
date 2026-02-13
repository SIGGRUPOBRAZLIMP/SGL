import { useState } from 'react'
import { captarEditais } from '../services/api'
import { Search, RefreshCw, CheckCircle, MapPin } from 'lucide-react'

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

export default function Captacao() {
  const [ufs, setUfs] = useState(['RJ'])
  const [modalidades, setModalidades] = useState([8])
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
      const r = await captarEditais({ modalidades, ufs })
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
        <p className="text-gray-500">Buscar novos editais no PNCP (Portal Nacional de Contratações Públicas)</p>
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
              Captando editais do PNCP...
            </>
          ) : (
            <>
              <Search size={22} />
              Captar Editais Agora
            </>
          )}
        </button>
      </div>

      {/* Resultado */}
      {error && (
        <div className="p-4 bg-danger-50 text-danger-700 rounded-lg mb-4">
          {error}
        </div>
      )}

      {result && (
        <div className="card bg-success-50 border-success-500">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle size={24} className="text-success-500" />
            <h3 className="text-lg font-semibold text-success-700">Captação Concluída!</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <ResultStat label="Encontrados no PNCP" value={result.total_encontrados} />
            <ResultStat label="Novos salvos" value={result.novos_salvos} highlight />
            <ResultStat label="Já existiam" value={result.duplicados} />
            <ResultStat label="Erros" value={result.erros} />
          </div>
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
