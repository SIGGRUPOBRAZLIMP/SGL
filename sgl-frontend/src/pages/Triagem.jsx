import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getEditais, decidirTriagem } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import { PRIORIDADES, formatCurrency, formatDate } from '../utils/constants'
import {
  CheckCircle, XCircle, Eye, AlertCircle, ChevronDown,
  ArrowUpDown, DollarSign, Calendar, MapPin, X
} from 'lucide-react'

const MOTIVOS_REJEICAO = [
  'Fora do segmento',
  'Região não atendida',
  'Valor muito baixo',
  'Valor muito alto',
  'Prazo inviável',
  'Sem condições de atendimento',
  'Produtos não disponíveis',
  'Margem insuficiente',
  'Outro',
]

export default function Triagem() {
  const [editais, setEditais] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)
  const navigate = useNavigate()

  // Filtros inline
  const [sortBy, setSortBy] = useState('data_publicacao')
  const [sortOrder, setSortOrder] = useState('desc')
  const [filterUf, setFilterUf] = useState('')
  const [filterValorMin, setFilterValorMin] = useState('')

  // Modal de rejeição
  const [rejectModal, setRejectModal] = useState(null) // edital ID
  const [rejectMotivo, setRejectMotivo] = useState('')
  const [rejectMotivoOutro, setRejectMotivoOutro] = useState('')
  const [rejectObservacao, setRejectObservacao] = useState('')

  // Modal de aprovação com prioridade
  const [approveModal, setApproveModal] = useState(null) // edital ID
  const [approvePrioridade, setApprovePrioridade] = useState('media')
  const [approveObservacao, setApproveObservacao] = useState('')

  useEffect(() => { loadPendentes() }, [])

  const loadPendentes = async () => {
    setLoading(true)
    try {
      const r = await getEditais({ status: 'captado', per_page: 100 })
      setEditais(r.data.editais || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Aprovar com prioridade
  const openApproveModal = (editalId) => {
    setApproveModal(editalId)
    setApprovePrioridade('media')
    setApproveObservacao('')
  }

  const handleAprovar = async () => {
    const editalId = approveModal
    setActionLoading(editalId)
    try {
      await decidirTriagem(editalId, {
        decisao: 'aprovado',
        prioridade: approvePrioridade,
        observacao: approveObservacao,
      })
      setEditais(prev => prev.filter(e => e.id !== editalId))
      setApproveModal(null)
    } catch (err) {
      console.error(err)
    } finally {
      setActionLoading(null)
    }
  }

  // Rejeitar com motivo
  const openRejectModal = (editalId) => {
    setRejectModal(editalId)
    setRejectMotivo('')
    setRejectMotivoOutro('')
    setRejectObservacao('')
  }

  const handleRejeitar = async () => {
    const editalId = rejectModal
    setActionLoading(editalId)
    try {
      const motivo = rejectMotivo === 'Outro' ? rejectMotivoOutro : rejectMotivo
      await decidirTriagem(editalId, {
        decisao: 'rejeitado',
        motivo_rejeicao: motivo,
        observacao: rejectObservacao,
        prioridade: 'baixa',
      })
      setEditais(prev => prev.filter(e => e.id !== editalId))
      setRejectModal(null)
    } catch (err) {
      console.error(err)
    } finally {
      setActionLoading(null)
    }
  }

  // Aprovar rápido sem modal
  const handleAprovarRapido = async (editalId) => {
    setActionLoading(editalId)
    try {
      await decidirTriagem(editalId, { decisao: 'aprovado', prioridade: 'media' })
      setEditais(prev => prev.filter(e => e.id !== editalId))
    } catch (err) {
      console.error(err)
    } finally {
      setActionLoading(null)
    }
  }

  // Sort and filter
  const sortedEditais = [...editais]
    .filter(e => {
      if (filterUf && e.uf !== filterUf) return false
      if (filterValorMin && (!e.valor_estimado || Number(e.valor_estimado) < Number(filterValorMin))) return false
      return true
    })
    .sort((a, b) => {
      let valA, valB
      switch (sortBy) {
        case 'valor_estimado':
          valA = Number(a.valor_estimado) || 0
          valB = Number(b.valor_estimado) || 0
          break
        case 'data_publicacao':
          valA = a.data_publicacao || ''
          valB = b.data_publicacao || ''
          break
        case 'data_certame':
          valA = a.data_certame || a.data_abertura_proposta || ''
          valB = b.data_certame || b.data_abertura_proposta || ''
          break
        case 'orgao':
          valA = a.orgao_razao_social || ''
          valB = b.orgao_razao_social || ''
          break
        default:
          valA = a.data_publicacao || ''
          valB = b.data_publicacao || ''
      }
      if (valA < valB) return sortOrder === 'asc' ? -1 : 1
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1
      return 0
    })

  const ufsPresentes = [...new Set(editais.map(e => e.uf).filter(Boolean))].sort()

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Triagem</h1>
          <p className="text-gray-500">{sortedEditais.length} edital(is) pendente(s) de avaliação</p>
        </div>
      </div>

      {/* Filtros e ordenação da triagem */}
      {editais.length > 0 && (
        <div className="card mb-4">
          <div className="flex flex-wrap gap-3 items-end">
            {/* Filtro UF */}
            <div className="w-28">
              <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1"><MapPin size={10} /> UF</label>
              <select value={filterUf} onChange={e => setFilterUf(e.target.value)} className="input-field text-sm">
                <option value="">Todas</option>
                {ufsPresentes.map(uf => <option key={uf} value={uf}>{uf}</option>)}
              </select>
            </div>

            {/* Filtro Valor mínimo */}
            <div className="w-40">
              <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1"><DollarSign size={10} /> Valor mín.</label>
              <input
                type="number"
                value={filterValorMin}
                onChange={e => setFilterValorMin(e.target.value)}
                className="input-field text-sm"
                placeholder="R$ 0"
                min="0"
              />
            </div>

            {/* Ordenar */}
            <div className="w-44">
              <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1"><ArrowUpDown size={10} /> Ordenar por</label>
              <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="input-field text-sm">
                <option value="data_publicacao">Data publicação</option>
                <option value="data_certame">Data certame</option>
                <option value="valor_estimado">Valor estimado</option>
                <option value="orgao">Órgão (A-Z)</option>
              </select>
            </div>

            {/* Ordem */}
            <div className="w-36">
              <label className="block text-xs text-gray-500 mb-1">Ordem</label>
              <select value={sortOrder} onChange={e => setSortOrder(e.target.value)} className="input-field text-sm">
                <option value="desc">Decrescente</option>
                <option value="asc">Crescente</option>
              </select>
            </div>

            {(filterUf || filterValorMin) && (
              <button onClick={() => { setFilterUf(''); setFilterValorMin('') }} className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 pb-2">
                <X size={12} /> Limpar
              </button>
            )}
          </div>
        </div>
      )}

      {/* Lista */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : sortedEditais.length === 0 ? (
        <div className="card text-center py-12">
          <CheckCircle size={48} className="mx-auto text-success-500 mb-4" />
          <h3 className="text-lg font-medium text-gray-600 mb-2">Triagem em dia!</h3>
          <p className="text-gray-400">Todos os editais foram avaliados. Capture mais editais no PNCP.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedEditais.map((e) => (
            <div key={e.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">{e.orgao_razao_social}</h3>
                    {e.uf && <span className="badge bg-gray-100 text-gray-600">{e.uf}</span>}
                    {e.srp && <span className="badge bg-indigo-50 text-indigo-600 text-xs">SRP</span>}
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{e.objeto_resumo || 'Sem descrição do objeto'}</p>
                  <div className="flex flex-wrap gap-4 text-xs text-gray-400">
                    {e.modalidade_nome && <span>{e.modalidade_nome}</span>}
                    {e.data_publicacao && <span>Publicado: {formatDate(e.data_publicacao)}</span>}
                    {e.data_abertura_proposta && <span>Abertura: {formatDate(e.data_abertura_proposta)}</span>}
                    {e.data_certame && <span className="font-medium text-gray-600">Certame: {formatDate(e.data_certame)}</span>}
                    {e.municipio && <span>{e.municipio}/{e.uf}</span>}
                  </div>
                </div>
                <div className="text-right ml-4">
                  {e.valor_estimado && (
                    <p className="text-lg font-bold text-primary-600 mb-2">{formatCurrency(e.valor_estimado)}</p>
                  )}
                  <div className="flex gap-2">
                    <button onClick={() => navigate(`/editais/${e.id}`)} className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1">
                      <Eye size={14} /> Ver
                    </button>
                    <button
                      onClick={() => openApproveModal(e.id)}
                      disabled={actionLoading === e.id}
                      className="btn-success text-xs py-1.5 px-3 flex items-center gap-1 disabled:opacity-50"
                    >
                      <CheckCircle size={14} /> Aprovar
                    </button>
                    <button
                      onClick={() => openRejectModal(e.id)}
                      disabled={actionLoading === e.id}
                      className="btn-danger text-xs py-1.5 px-3 flex items-center gap-1 disabled:opacity-50"
                    >
                      <XCircle size={14} /> Rejeitar
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* === Modal Aprovar === */}
      {approveModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <CheckCircle size={20} className="text-green-500" /> Aprovar Edital
              </h2>
              <button onClick={() => setApproveModal(null)} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Prioridade</label>
                <div className="flex gap-2">
                  {PRIORIDADES.map(p => (
                    <button
                      key={p.value}
                      onClick={() => setApprovePrioridade(p.value)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex-1 ${
                        approvePrioridade === p.value
                          ? p.value === 'urgente' ? 'bg-red-600 text-white'
                          : p.value === 'alta' ? 'bg-orange-500 text-white'
                          : p.value === 'media' ? 'bg-yellow-500 text-white'
                          : 'bg-gray-500 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observação (opcional)</label>
                <textarea
                  value={approveObservacao}
                  onChange={e => setApproveObservacao(e.target.value)}
                  className="input-field"
                  rows={2}
                  placeholder="Anotação sobre o edital..."
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button onClick={handleAprovar} disabled={actionLoading} className="btn-success flex-1 py-2.5 disabled:opacity-50">
                  {actionLoading ? 'Aprovando...' : 'Confirmar Aprovação'}
                </button>
                <button onClick={() => setApproveModal(null)} className="btn-secondary">Cancelar</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* === Modal Rejeitar === */}
      {rejectModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <XCircle size={20} className="text-red-500" /> Rejeitar Edital
              </h2>
              <button onClick={() => setRejectModal(null)} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Motivo da rejeição *</label>
                <div className="flex flex-wrap gap-2">
                  {MOTIVOS_REJEICAO.map(m => (
                    <button
                      key={m}
                      onClick={() => setRejectMotivo(m)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        rejectMotivo === m ? 'bg-red-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>

              {rejectMotivo === 'Outro' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Especifique o motivo</label>
                  <input
                    type="text"
                    value={rejectMotivoOutro}
                    onChange={e => setRejectMotivoOutro(e.target.value)}
                    className="input-field"
                    placeholder="Descreva o motivo..."
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observação (opcional)</label>
                <textarea
                  value={rejectObservacao}
                  onChange={e => setRejectObservacao(e.target.value)}
                  className="input-field"
                  rows={2}
                  placeholder="Anotação adicional..."
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleRejeitar}
                  disabled={actionLoading || (!rejectMotivo || (rejectMotivo === 'Outro' && !rejectMotivoOutro))}
                  className="btn-danger flex-1 py-2.5 disabled:opacity-50"
                >
                  {actionLoading ? 'Rejeitando...' : 'Confirmar Rejeição'}
                </button>
                <button onClick={() => setRejectModal(null)} className="btn-secondary">Cancelar</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
