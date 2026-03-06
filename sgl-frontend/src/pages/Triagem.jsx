import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getEditais, decidirTriagem } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import { PRIORIDADES, UFS, MODALIDADES, formatCurrency, formatDate } from '../utils/constants'
import {
  CheckCircle, XCircle, Eye, AlertCircle, ChevronDown,
  ArrowUpDown, DollarSign, Calendar, MapPin, X, Search,
  CheckSquare, Square, ListChecks, SlidersHorizontal, ChevronUp
} from 'lucide-react'
import api from '../services/api'

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

const PLATAFORMAS = [
  { value: 'pncp', label: 'PNCP' },
  { value: 'bbmnet', label: 'BBMNET' },
  { value: 'licitardigital', label: 'Licitar Digital' },
  { value: 'comprasgov', label: 'ComprasGov' },
]

export default function Triagem() {
  const [editais, setEditais] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)
  const [bulkLoading, setBulkLoading] = useState(false)
  const navigate = useNavigate()

  // Filtros
  const [showFilters, setShowFilters] = useState(false)
  const [filterUf, setFilterUf] = useState('')
  const [filterPlataforma, setFilterPlataforma] = useState('')
  const [filterModalidade, setFilterModalidade] = useState('')
  const [filterBusca, setFilterBusca] = useState('')
  const [filterValorMin, setFilterValorMin] = useState('')
  const [filterDataPubInicio, setFilterDataPubInicio] = useState('')
  const [filterDataPubFim, setFilterDataPubFim] = useState('')
  const [sortBy, setSortBy] = useState('data_publicacao')
  const [sortOrder, setSortOrder] = useState('desc')

  // Seleção em massa
  const [selected, setSelected] = useState(new Set())

  // Modal de rejeição
  const [rejectModal, setRejectModal] = useState(null)
  const [rejectMotivo, setRejectMotivo] = useState('')
  const [rejectMotivoOutro, setRejectMotivoOutro] = useState('')
  const [rejectObservacao, setRejectObservacao] = useState('')

  // Modal de aprovação com prioridade
  const [approveModal, setApproveModal] = useState(null)
  const [approvePrioridade, setApprovePrioridade] = useState('media')
  const [approveObservacao, setApproveObservacao] = useState('')

  useEffect(() => { loadPendentes() }, [])

  const loadPendentes = async () => {
    setLoading(true)
    try {
      const r = await getEditais({ status: 'captado', per_page: 200 })
      setEditais(r.data.editais || [])
      setSelected(new Set())
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // ========== FILTROS ==========
  const activeFiltersCount = [filterUf, filterPlataforma, filterModalidade, filterBusca, filterValorMin, filterDataPubInicio, filterDataPubFim].filter(Boolean).length

  const clearFilters = () => {
    setFilterUf(''); setFilterPlataforma(''); setFilterModalidade('')
    setFilterBusca(''); setFilterValorMin('')
    setFilterDataPubInicio(''); setFilterDataPubFim('')
  }

  const sortedEditais = [...editais]
    .filter(e => {
      if (filterUf && e.uf !== filterUf) return false
      if (filterPlataforma && e.plataforma_origem !== filterPlataforma) return false
      if (filterModalidade && !e.modalidade_nome?.toLowerCase().includes(filterModalidade.toLowerCase())) return false
      if (filterBusca) {
        const busca = filterBusca.toLowerCase()
        const match = (e.objeto_resumo || '').toLowerCase().includes(busca) ||
          (e.orgao_razao_social || '').toLowerCase().includes(busca) ||
          (e.numero_processo || '').toLowerCase().includes(busca)
        if (!match) return false
      }
      if (filterValorMin && (!e.valor_estimado || Number(e.valor_estimado) < Number(filterValorMin))) return false
      if (filterDataPubInicio && e.data_publicacao && e.data_publicacao < filterDataPubInicio) return false
      if (filterDataPubFim && e.data_publicacao && e.data_publicacao > filterDataPubFim + 'T23:59:59') return false
      return true
    })
    .sort((a, b) => {
      let valA, valB
      switch (sortBy) {
        case 'valor_estimado':
          valA = Number(a.valor_estimado) || 0
          valB = Number(b.valor_estimado) || 0
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

  // ========== SELEÇÃO EM MASSA ==========
  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selected.size === sortedEditais.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(sortedEditais.map(e => e.id)))
    }
  }

  const allSelected = sortedEditais.length > 0 && selected.size === sortedEditais.length

  // ========== AÇÕES INDIVIDUAIS ==========
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
      setSelected(prev => { const n = new Set(prev); n.delete(editalId); return n })
      setApproveModal(null)
    } catch (err) {
      console.error(err)
    } finally {
      setActionLoading(null)
    }
  }

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
      setSelected(prev => { const n = new Set(prev); n.delete(editalId); return n })
      setRejectModal(null)
    } catch (err) {
      console.error(err)
    } finally {
      setActionLoading(null)
    }
  }

  // ========== AÇÕES EM MASSA ==========
  const openBulkApprove = () => {
    if (selected.size === 0) return
    setApproveModal('bulk')
    setApprovePrioridade('media')
    setApproveObservacao('')
  }

  const openBulkReject = () => {
    if (selected.size === 0) return
    setRejectModal('bulk')
    setRejectMotivo('')
    setRejectMotivoOutro('')
    setRejectObservacao('')
  }

  const handleBulkAprovar = async () => {
    setBulkLoading(true)
    try {
      const ids = [...selected]
      await api.post('/triagem/bulk', {
        edital_ids: ids,
        decisao: 'aprovado',
        prioridade: approvePrioridade,
        observacao: approveObservacao,
      })
      setEditais(prev => prev.filter(e => !selected.has(e.id)))
      setSelected(new Set())
      setApproveModal(null)
    } catch (err) {
      console.error(err)
      alert('Erro na aprovação em massa: ' + (err.response?.data?.error || err.message))
    } finally {
      setBulkLoading(false)
    }
  }

  const handleBulkRejeitar = async () => {
    setBulkLoading(true)
    try {
      const ids = [...selected]
      const motivo = rejectMotivo === 'Outro' ? rejectMotivoOutro : rejectMotivo
      await api.post('/triagem/bulk', {
        edital_ids: ids,
        decisao: 'rejeitado',
        motivo_rejeicao: motivo,
        observacao: rejectObservacao,
        prioridade: 'baixa',
      })
      setEditais(prev => prev.filter(e => !selected.has(e.id)))
      setSelected(new Set())
      setRejectModal(null)
    } catch (err) {
      console.error(err)
      alert('Erro na rejeição em massa: ' + (err.response?.data?.error || err.message))
    } finally {
      setBulkLoading(false)
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Triagem</h1>
          <p className="text-gray-500">{sortedEditais.length} edital(is) pendente(s) de avaliação</p>
        </div>
      </div>

      {/* Filtros */}
      {editais.length > 0 && (
        <div className="card mb-4">
          <div className="flex flex-wrap gap-3 items-end">
            {/* Busca por objeto/órgão */}
            <div className="flex-1 min-w-[180px]">
              <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1"><Search size={10} /> Objeto / Órgão</label>
              <input
                type="text"
                value={filterBusca}
                onChange={e => setFilterBusca(e.target.value)}
                className="input-field text-sm"
                placeholder="Buscar no objeto ou órgão..."
              />
            </div>

            {/* UF - lista completa */}
            <div className="w-28">
              <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1"><MapPin size={10} /> UF</label>
              <select value={filterUf} onChange={e => setFilterUf(e.target.value)} className="input-field text-sm">
                <option value="">Todas</option>
                {UFS.map(uf => <option key={uf} value={uf}>{uf}</option>)}
              </select>
            </div>

            {/* Plataforma */}
            <div className="w-36">
              <label className="block text-xs text-gray-500 mb-1">Plataforma</label>
              <select value={filterPlataforma} onChange={e => setFilterPlataforma(e.target.value)} className="input-field text-sm">
                <option value="">Todas</option>
                {PLATAFORMAS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>

            {/* Ordenar */}
            <div className="w-40">
              <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1"><ArrowUpDown size={10} /> Ordenar</label>
              <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="input-field text-sm">
                <option value="data_publicacao">Data publicação</option>
                <option value="data_certame">Data certame</option>
                <option value="valor_estimado">Valor estimado</option>
                <option value="orgao">Órgão (A-Z)</option>
              </select>
            </div>

            <div className="w-32">
              <label className="block text-xs text-gray-500 mb-1">Ordem</label>
              <select value={sortOrder} onChange={e => setSortOrder(e.target.value)} className="input-field text-sm">
                <option value="desc">Decrescente</option>
                <option value="asc">Crescente</option>
              </select>
            </div>

            {/* Toggle mais filtros */}
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`btn-secondary text-xs py-2.5 flex items-center gap-1 ${activeFiltersCount > 0 ? 'ring-2 ring-primary-300' : ''}`}
            >
              <SlidersHorizontal size={14} />
              Mais
              {activeFiltersCount > 0 && (
                <span className="bg-primary-600 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center ml-1">
                  {activeFiltersCount}
                </span>
              )}
              {showFilters ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>

            {activeFiltersCount > 0 && (
              <button onClick={clearFilters} className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 pb-2">
                <X size={12} /> Limpar
              </button>
            )}
          </div>

          {/* Filtros expandidos */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-2 md:grid-cols-4 gap-3">
              {/* Modalidade */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Modalidade</label>
                <select value={filterModalidade} onChange={e => setFilterModalidade(e.target.value)} className="input-field text-sm">
                  <option value="">Todas</option>
                  {MODALIDADES.map(m => <option key={m.id} value={m.nome}>{m.nome}</option>)}
                </select>
              </div>

              {/* Valor mínimo */}
              <div>
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

              {/* Data publicação início */}
              <div>
                <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1"><Calendar size={10} /> Publicado desde</label>
                <input type="date" value={filterDataPubInicio} onChange={e => setFilterDataPubInicio(e.target.value)} className="input-field text-sm" />
              </div>

              {/* Data publicação fim */}
              <div>
                <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1"><Calendar size={10} /> Publicado até</label>
                <input type="date" value={filterDataPubFim} onChange={e => setFilterDataPubFim(e.target.value)} className="input-field text-sm" />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Barra de ações em massa */}
      {editais.length > 0 && (
        <div className="flex items-center justify-between mb-4 px-1">
          <div className="flex items-center gap-3">
            <button onClick={toggleSelectAll} className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800">
              {allSelected ? <CheckSquare size={18} className="text-primary-600" /> : <Square size={18} />}
              {allSelected ? 'Desmarcar todos' : 'Selecionar todos'}
            </button>
            {selected.size > 0 && (
              <span className="text-sm text-primary-600 font-medium">
                {selected.size} selecionado(s)
              </span>
            )}
          </div>

          {selected.size > 0 && (
            <div className="flex gap-2">
              <button
                onClick={openBulkApprove}
                className="btn-success text-xs py-1.5 px-4 flex items-center gap-1"
              >
                <CheckCircle size={14} /> Aprovar ({selected.size})
              </button>
              <button
                onClick={openBulkReject}
                className="btn-danger text-xs py-1.5 px-4 flex items-center gap-1"
              >
                <XCircle size={14} /> Rejeitar ({selected.size})
              </button>
            </div>
          )}
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
          <h3 className="text-lg font-medium text-gray-600 mb-2">
            {editais.length === 0 ? 'Triagem em dia!' : 'Nenhum edital com esses filtros'}
          </h3>
          <p className="text-gray-400">
            {editais.length === 0
              ? 'Todos os editais foram avaliados. Capture mais editais no PNCP.'
              : 'Tente ajustar os filtros para ver mais editais.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {sortedEditais.map((e) => (
            <div key={e.id} className={`card hover:shadow-md transition-shadow ${selected.has(e.id) ? 'ring-2 ring-primary-400 bg-primary-50/30' : ''}`}>
              <div className="flex items-start gap-3">
                {/* Checkbox */}
                <button onClick={() => toggleSelect(e.id)} className="mt-1 flex-shrink-0">
                  {selected.has(e.id)
                    ? <CheckSquare size={20} className="text-primary-600" />
                    : <Square size={20} className="text-gray-300 hover:text-gray-500" />
                  }
                </button>

                {/* Conteúdo */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h3 className="font-semibold text-gray-900">{e.orgao_razao_social}</h3>
                    {e.uf && <span className="badge bg-gray-100 text-gray-600">{e.uf}</span>}
                    {e.plataforma_origem && <PlataformaBadge plataforma={e.plataforma_origem} />}
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

                {/* Valor + Ações */}
                <div className="text-right ml-4 flex-shrink-0">
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

      {/* === Modal Aprovar (individual ou bulk) === */}
      {approveModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <CheckCircle size={20} className="text-green-500" />
                {approveModal === 'bulk' ? `Aprovar ${selected.size} Editais` : 'Aprovar Edital'}
              </h2>
              <button onClick={() => setApproveModal(null)} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>

            {approveModal === 'bulk' && (
              <div className="mb-4 p-3 bg-green-50 rounded-lg text-sm text-green-700">
                <ListChecks size={16} className="inline mr-1" />
                {selected.size} edital(is) serão aprovados com a prioridade selecionada.
              </div>
            )}

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
                <button
                  onClick={approveModal === 'bulk' ? handleBulkAprovar : handleAprovar}
                  disabled={actionLoading || bulkLoading}
                  className="btn-success flex-1 py-2.5 disabled:opacity-50"
                >
                  {(actionLoading || bulkLoading) ? 'Aprovando...' : approveModal === 'bulk' ? `Aprovar ${selected.size} Editais` : 'Confirmar Aprovação'}
                </button>
                <button onClick={() => setApproveModal(null)} className="btn-secondary">Cancelar</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* === Modal Rejeitar (individual ou bulk) === */}
      {rejectModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <XCircle size={20} className="text-red-500" />
                {rejectModal === 'bulk' ? `Rejeitar ${selected.size} Editais` : 'Rejeitar Edital'}
              </h2>
              <button onClick={() => setRejectModal(null)} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>

            {rejectModal === 'bulk' && (
              <div className="mb-4 p-3 bg-red-50 rounded-lg text-sm text-red-700">
                <ListChecks size={16} className="inline mr-1" />
                {selected.size} edital(is) serão rejeitados com o motivo selecionado.
              </div>
            )}

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
                  onClick={rejectModal === 'bulk' ? handleBulkRejeitar : handleRejeitar}
                  disabled={actionLoading || bulkLoading || (!rejectMotivo || (rejectMotivo === 'Outro' && !rejectMotivoOutro))}
                  className="btn-danger flex-1 py-2.5 disabled:opacity-50"
                >
                  {(actionLoading || bulkLoading) ? 'Rejeitando...' : rejectModal === 'bulk' ? `Rejeitar ${selected.size} Editais` : 'Confirmar Rejeição'}
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

const PLATAFORMA_CONFIG = {
  pncp:            { label: 'PNCP',     bg: 'bg-blue-100',   text: 'text-blue-700' },
  bbmnet:          { label: 'BBMNET',   bg: 'bg-green-100',  text: 'text-green-700' },
  licitardigital:  { label: 'Licitar',  bg: 'bg-purple-100', text: 'text-purple-700' },
  comprasgov:      { label: 'ComprasGov', bg: 'bg-orange-100', text: 'text-orange-700' },
}

function PlataformaBadge({ plataforma }) {
  const config = PLATAFORMA_CONFIG[plataforma] || { label: plataforma || '—', bg: 'bg-gray-100', text: 'text-gray-600' }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  )
}
