import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { getDashboardStats, limparRejeitados } from '../services/api'
import { FileText, Filter, CheckCircle, XCircle, AlertCircle, Clock, Trash2, Globe, Shield, Zap } from 'lucide-react'

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
  const [limpando, setLimpando] = useState(false)
  const [limpResult, setLimpResult] = useState(null)

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

  const handleLimpar = async () => {
    if (!window.confirm('Remover editais rejeitados com mais de 7 dias?')) return
    setLimpando(true)
    try {
      const r = await limparRejeitados()
      setLimpResult(r.data)
      loadStats()
    } catch (err) {
      setLimpResult({ erro: 'Erro ao limpar' })
    } finally {
      setLimpando(false)
      setTimeout(() => setLimpResult(null), 5000)
    }
  }

  const formatDate = (iso) => {
    if (!iso) return 'Nunca'
    const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z')
    return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Olá, {user?.nome}!</h1>
          <p className="text-gray-500">Bem-vindo ao painel do SGL</p>
        </div>
      </div>

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

          {/* Últimas Captações + Manutenção */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Clock size={20} className="text-primary-600" /> Últimas Captações
              </h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Globe size={16} className="text-blue-600" />
                    <span className="font-medium text-blue-700">PNCP</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm text-gray-600">{formatDate(stats?.ultimas_captacoes?.pncp)}</span>
                    <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{stats?.por_plataforma?.pncp || 0}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Shield size={16} className="text-green-600" />
                    <span className="font-medium text-green-700">BBMNET</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm text-gray-600">{formatDate(stats?.ultimas_captacoes?.bbmnet)}</span>
                    <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">{stats?.por_plataforma?.bbmnet || 0}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Zap size={16} className="text-purple-600" />
                    <span className="font-medium text-purple-700">Licitar Digital</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm text-gray-600">{formatDate(stats?.ultimas_captacoes?.licitardigital)}</span>
                    <span className="ml-2 text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">{stats?.por_plataforma?.licitardigital || 0}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Trash2 size={20} className="text-red-500" /> Manutenção
              </h2>
              <p className="text-sm text-gray-500 mb-4">
                Remove editais rejeitados com mais de 7 dias para liberar espaço no banco.
              </p>
              <button onClick={handleLimpar} disabled={limpando}
                className="w-full py-2 px-4 rounded-lg bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 font-medium text-sm flex items-center justify-center gap-2 disabled:opacity-50">
                <Trash2 size={16} />
                {limpando ? 'Limpando...' : `Limpar Rejeitados (${stats?.rejeitados || 0})`}
              </button>
              {limpResult && (
                <div className={`mt-3 p-2 rounded text-sm ${limpResult.erro ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
                  {limpResult.erro || `✅ ${limpResult.removidos} editais removidos`}
                </div>
              )}
            </div>
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
              <p className="text-gray-400 mb-4">Vá em Captação para buscar editais do PNCP, BBMNET e Licitar Digital</p>
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
