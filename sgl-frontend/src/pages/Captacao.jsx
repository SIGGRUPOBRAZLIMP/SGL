import { useState } from 'react'
import { captarPNCP, captarBBMNET, captarLicitar } from '../services/api'
import { Search, RefreshCw, CheckCircle, MapPin, Calendar, AlertTriangle, Globe, Shield, Zap } from 'lucide-react'

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
  { dias: 3, nome: '3 dias' },
  { dias: 7, nome: '7 dias' },
  { dias: 15, nome: '15 dias' },
  { dias: 30, nome: '30 dias' },
]

export default function Captacao() {
  const [ufs, setUfs] = useState(['RJ', 'MG', 'SP', 'ES'])
  const [modalidades, setModalidades] = useState([8])
  const [periodoDias, setPeriodoDias] = useState(3)

  // Estado individual por plataforma
  const [pncp, setPncp] = useState({ loading: false, result: null, error: '' })
  const [bbmnet, setBbmnet] = useState({ loading: false, result: null, error: '' })
  const [licitar, setLicitar] = useState({ loading: false, result: null, error: '' })

  const toggleUf = (uf) => setUfs(prev => prev.includes(uf) ? prev.filter(u => u !== uf) : [...prev, uf])
  const toggleModalidade = (id) => setModalidades(prev => prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id])

  const handleCaptarPNCP = async () => {
    setPncp({ loading: true, result: null, error: '' })
    try {
      const r = await captarPNCP({ modalidades, ufs, periodo_dias: periodoDias })
      setPncp({ loading: false, result: r.data, error: '' })
    } catch (err) {
      setPncp({ loading: false, result: null, error: err.response?.data?.erro || 'Erro ao captar PNCP' })
    }
  }

  const handleCaptarBBMNET = async () => {
    setBbmnet({ loading: true, result: null, error: '' })
    try {
      const r = await captarBBMNET({ ufs, periodo_dias: periodoDias })
      setBbmnet({ loading: false, result: r.data, error: '' })
    } catch (err) {
      setBbmnet({ loading: false, result: null, error: err.response?.data?.erro || 'Erro ao captar BBMNET' })
    }
  }

  const handleCaptarLicitar = async () => {
    setLicitar({ loading: false, result: null, error: 'Captação via script local (C:\\SGL-Licitar\\captar_licitar.bat). Cloudflare bloqueia IPs cloud.' })
  }

  const handleCaptarTodas = () => {
    handleCaptarPNCP()
    handleCaptarBBMNET()
    handleCaptarLicitar()
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Captação de Editais</h1>
        <p className="text-gray-500">Buscar novos editais — cada plataforma roda independente</p>
      </div>

      {/* Filtros Globais */}
      <div className="card mb-6">
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-1 flex items-center gap-1">
              <Calendar size={14} /> Período
            </h3>
            <div className="flex gap-1">
              {PERIODOS.map(p => (
                <button key={p.dias} onClick={() => setPeriodoDias(p.dias)}
                  className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                    periodoDias === p.dias ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}>{p.nome}</button>
              ))}
            </div>
          </div>
        </div>

        {/* UFs */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-1">
              <MapPin size={14} /> Estados
            </h3>
            <button onClick={() => setUfs(['RJ','SP','MG','ES'])} className="text-xs text-primary-600 hover:underline">Sudeste</button>
            <button onClick={() => setUfs([...UFS])} className="text-xs text-primary-600 hover:underline">Todos</button>
            <button onClick={() => setUfs([])} className="text-xs text-gray-400 hover:underline">Limpar</button>
          </div>
          <div className="flex flex-wrap gap-1">
            {UFS.map(uf => (
              <button key={uf} onClick={() => toggleUf(uf)}
                className={`w-10 h-8 rounded text-xs font-medium transition-colors ${
                  ufs.includes(uf) ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}>{uf}</button>
            ))}
          </div>
        </div>

        {/* Modalidades (colapsável) */}
        <details className="mb-2">
          <summary className="text-sm font-semibold text-gray-700 cursor-pointer">Modalidades (PNCP)</summary>
          <div className="flex flex-wrap gap-1 mt-2">
            {MODALIDADES.map(m => (
              <button key={m.id} onClick={() => toggleModalidade(m.id)}
                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                  modalidades.includes(m.id) ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}>{m.nome}</button>
            ))}
          </div>
        </details>
      </div>

      {/* Botão Captar Todas */}
      <button onClick={handleCaptarTodas}
        disabled={pncp.loading || bbmnet.loading || licitar.loading}
        className="btn-primary w-full py-3 text-base flex items-center justify-center gap-2 mb-6 disabled:opacity-50">
        <Search size={20} />
        Captar Todas as Plataformas — últimos {periodoDias} dia(s)
      </button>

      {/* 3 Plataformas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* PNCP */}
        <PlatformCard
          name="PNCP"
          subtitle="Portal Nacional de Contratações Públicas"
          icon={<Globe size={20} />}
          color="blue"
          loading={pncp.loading}
          result={pncp.result}
          error={pncp.error}
          onCaptar={handleCaptarPNCP}
          renderResult={() => pncp.result && (
            <div className="space-y-2">
              <StatRow label="Encontrados" value={pncp.result.total_encontrados} />
              <StatRow label="Novos salvos" value={pncp.result.novos_salvos} highlight />
              <StatRow label="Duplicados" value={pncp.result.duplicados} />
              <StatRow label="Filtrados" value={pncp.result.filtrados} />
              {pncp.result.detalhes_uf && Object.entries(pncp.result.detalhes_uf).map(([uf, s]) => (
                <p key={uf} className="text-xs text-gray-500">{uf}: {s.encontrados} enc, {s.novos_salvos} novos</p>
              ))}
            </div>
          )}
        />

        {/* BBMNET */}
        <PlatformCard
          name="BBMNET"
          subtitle="Bolsa Brasileira de Mercadorias"
          icon={<Shield size={20} />}
          color="green"
          loading={bbmnet.loading}
          result={bbmnet.result}
          error={bbmnet.error}
          onCaptar={handleCaptarBBMNET}
          renderResult={() => bbmnet.result?.stats && (
            <div className="space-y-2">
              <StatRow label="Encontrados" value={bbmnet.result.stats.total_encontrados || 0} />
              <StatRow label="Novos salvos" value={bbmnet.result.stats.novos_salvos || 0} highlight />
              <StatRow label="Duplicados" value={bbmnet.result.stats.duplicados || 0} />
              {bbmnet.result.stats.por_uf && Object.entries(bbmnet.result.stats.por_uf).map(([uf, s]) => (
                <p key={uf} className="text-xs text-gray-500">{uf}: {s.encontrados || 0} enc, {s.convertidos || 0} conv</p>
              ))}
            </div>
          )}
        />

        {/* Licitar Digital */}
        <PlatformCard
          name="Licitar Digital"
          subtitle="Plataforma de Licitações Digitais"
          icon={<Zap size={20} />}
          color="purple"
          loading={licitar.loading}
          result={licitar.result}
          error={licitar.error}
          onCaptar={handleCaptarLicitar}
          renderResult={() => licitar.result && (
            <div className="space-y-2">
              <StatRow label="Encontrados" value={licitar.result.total_encontrados || 0} />
              <StatRow label="Novos salvos" value={licitar.result.novos_salvos || 0} highlight />
              <StatRow label="Duplicados" value={licitar.result.duplicados || 0} />
            </div>
          )}
        />
      </div>
    </div>
  )
}

function PlatformCard({ name, subtitle, icon, color, loading, result, error, onCaptar, renderResult }) {
  const colors = {
    blue: { bg: 'bg-blue-50', border: 'border-blue-200', btn: 'bg-blue-600 hover:bg-blue-700', text: 'text-blue-700', light: 'text-blue-500' },
    green: { bg: 'bg-green-50', border: 'border-green-200', btn: 'bg-green-600 hover:bg-green-700', text: 'text-green-700', light: 'text-green-500' },
    purple: { bg: 'bg-purple-50', border: 'border-purple-200', btn: 'bg-purple-600 hover:bg-purple-700', text: 'text-purple-700', light: 'text-purple-500' },
  }
  const c = colors[color] || colors.blue

  return (
    <div className={`rounded-xl border ${c.border} ${c.bg} p-4`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={c.text}>{icon}</span>
        <h3 className={`font-bold ${c.text}`}>{name}</h3>
      </div>
      <p className="text-xs text-gray-500 mb-3">{subtitle}</p>

      <button onClick={onCaptar} disabled={loading}
        className={`w-full py-2 px-3 rounded-lg text-white text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50 ${c.btn}`}>
        {loading ? <><RefreshCw size={16} className="animate-spin" /> Captando...</> : <><Search size={16} /> Captar</>}
      </button>

      {error && (
        <div className="mt-3 p-2 bg-red-50 rounded text-xs text-red-600 flex items-center gap-1">
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {result && !error && (
        <div className="mt-3 p-2 bg-white bg-opacity-70 rounded">
          <div className="flex items-center gap-1 mb-2">
            <CheckCircle size={14} className={c.light} />
            <span className={`text-xs font-semibold ${c.text}`}>Concluído!</span>
          </div>
          {renderResult()}
        </div>
      )}
    </div>
  )
}

function StatRow({ label, value, highlight }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-xs text-gray-600">{label}</span>
      <span className={`text-sm font-bold ${highlight ? 'text-green-600' : 'text-gray-800'}`}>{value ?? 0}</span>
    </div>
  )
}
