import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { getDashboardStats, captarEditais } from '../services/api'
import { FileText, Filter, CheckCircle, XCircle, TrendingUp, RefreshCw, AlertCircle } from 'lucide-react'

function StatCard({ icon: Icon, label, value, color, sub }) {
  const colors = {
    blue: 'bg-primary-50 text-primary-600',
    green: 'bg-success-50 text-success-500',
    yellow: 'bg-warning-50 text-warning-500',
    red: 'bg-danger-50 text-danger-500',
  }
  return (
    <div className="card flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colors[color]}`}>
        <Icon size={24} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value ?? '—'}</p>
        <p className="text-sm text-gray-500">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [captando, setCaptando] = useState(false)
  const [captResult, setCaptResult] = useState(null)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      const r = await getDashboardStats()
      setStats(r.data)
    } catch (err) {
      console.error('Erro ao carregar stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCaptarRapido = async () => {
    setCaptando(true)
    setCaptResult(null)
    try {
      const r = await captarEditais({ modalidades: [8], ufs: ['RJ', 'SP', 'MG', 'ES'] })
      setCaptResult(r.data)
      loadStats()
    } catch (err) {
      setCaptResult({ erro: err.response?.data?.error || 'Erro na captação' })
    } finally {
      setCaptando(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Olá, {user?.nome}!</h1>
          <p className="text-gray-500">Bem-vindo ao painel do SGL</p>
        </div>
        <button onClick={handleCaptarRapido} disabled={captando} className="btn-primary flex items-center gap-2 disabled:opacity-50">
          <RefreshCw size={18} className={captando ? 'animate-spin' : ''} />
          {captando ? 'Captando...' : 'Captar Pregões'}
        </button>
      </div>

      {captResult && (
        <div className={`mb-6 p-4 rounded-lg ${captResult.erro ? 'bg-danger-50 text-danger-700' : 'bg-success-50 text-success-700'}`}>
          {captResult.erro ? (
            <span>{captResult.erro}</span>
          ) : (
            <span>✅ Captação concluída: {captResult.novos_salvos} novos editais, {captResult.duplicados} já existiam, {captResult.total_encontrados} encontrados no PNCP</span>
          )}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard icon={FileText} label="Editais Captados" value={stats?.editais_captados ?? 0} color="blue" />
            <StatCard icon={Filter} label="Pendentes Triagem" value={stats?.pendentes_triagem ?? 0} color="yellow" />
            <StatCard icon={CheckCircle} label="Aprovados" value={stats?.aprovados ?? 0} color="green" />
            <StatCard icon={XCircle} label="Rejeitados" value={stats?.rejeitados ?? 0} color="red" />
          </div>

          {stats?.editais_recentes?.length > 0 && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Últimos Editais Captados</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-3 px-4 text-gray-500 font-medium">Órgão</th>
                      <th className="text-left py-3 px-4 text-gray-500 font-medium">Objeto</th>
                      <th className="text-left py-3 px-4 text-gray-500 font-medium">UF</th>
                      <th className="text-right py-3 px-4 text-gray-500 font-medium">Valor Est.</th>
                      <th className="text-left py-3 px-4 text-gray-500 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.editais_recentes.map((e) => (
                      <tr key={e.id} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="py-3 px-4 font-medium text-gray-900">{e.orgao_razao_social?.substring(0, 40)}</td>
                        <td className="py-3 px-4 text-gray-600">{e.objeto_resumo?.substring(0, 60) || '—'}</td>
                        <td className="py-3 px-4 text-gray-600">{e.uf || '—'}</td>
                        <td className="py-3 px-4 text-right text-gray-900 font-medium">
                          {e.valor_estimado ? `R$ ${Number(e.valor_estimado).toLocaleString('pt-BR')}` : '—'}
                        </td>
                        <td className="py-3 px-4">
                          <StatusBadge status={e.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {(!stats?.editais_recentes || stats.editais_recentes.length === 0) && (
            <div className="card text-center py-12">
              <AlertCircle size={48} className="mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-600 mb-2">Nenhum edital captado ainda</h3>
              <p className="text-gray-400 mb-4">Clique em "Captar Pregões" para buscar editais do PNCP e BBMNET</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function StatusBadge({ status }) {
  const styles = {
    captado: 'bg-blue-100 text-blue-700',
    aprovado: 'bg-green-100 text-green-700',
    rejeitado: 'bg-red-100 text-red-700',
    em_processo: 'bg-yellow-100 text-yellow-700',
  }
  return (
    <span className={`badge ${styles[status] || 'bg-gray-100 text-gray-700'}`}>
      {status || 'captado'}
    </span>
  )
}
