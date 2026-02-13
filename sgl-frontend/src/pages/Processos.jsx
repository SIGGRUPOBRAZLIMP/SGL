import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getProcessos, criarProcesso, atualizarProcesso,
  importarItensAI, analisarViabilidade, getEditais
} from '../services/api'
import StatusBadge from '../components/StatusBadge'
import { STATUS_PROCESSO, PRIORIDADES, formatCurrency, formatDate } from '../utils/constants'
import {
  Briefcase, Plus, Search, Filter, ChevronLeft, ChevronRight,
  X, Brain, CheckCircle, AlertTriangle, BarChart3, Eye,
  SlidersHorizontal, Calendar, DollarSign, User, ArrowUpDown,
  LayoutGrid, List, RefreshCw, Loader2, ChevronDown, ChevronUp
} from 'lucide-react'

export default function Processos() {
  const navigate = useNavigate()

  // --- Dados ---
  const [processos, setProcessos] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [editaisDisponiveis, setEditaisDisponiveis] = useState([])

  // --- Paginação ---
  const [page, setPage] = useState(1)
  const perPage = 20

  // --- View mode ---
  const [viewMode, setViewMode] = useState('table') // 'table' | 'kanban' | 'cards'

  // --- Filtros ---
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({
    busca: '',
    status: '',
    prioridade: '',
    cotador: '',
    data_inicio: '',
    data_fim: '',
    valor_min: '',
    valor_max: '',
    margem_min: '',
    com_itens_ai: '',
    viabilidade: '',
    ordenar_por: 'created_at',
    ordem: 'desc',
  })

  // --- Modal novo processo ---
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({
    edital_id: '', margem_minima: '15', prioridade: 'media', observacoes: ''
  })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  // --- Ações AI ---
  const [aiLoading, setAiLoading] = useState(null)
  const [actionResult, setActionResult] = useState(null)

  // --- Filtros ativos count ---
  const activeFiltersCount = useMemo(() => {
    return Object.entries(filters).filter(([key, val]) =>
      val !== '' && !['ordenar_por', 'ordem', 'busca'].includes(key)
    ).length
  }, [filters])

  // === Load Data ===
  useEffect(() => { loadProcessos() }, [page, filters.ordenar_por, filters.ordem])

  const loadProcessos = async () => {
    setLoading(true)
    try {
      const params = { page, per_page: perPage }
      if (filters.busca) params.busca = filters.busca
      if (filters.status) params.status = filters.status
      if (filters.prioridade) params.prioridade = filters.prioridade
      if (filters.cotador) params.cotador = filters.cotador
      if (filters.data_inicio) params.data_inicio = filters.data_inicio
      if (filters.data_fim) params.data_fim = filters.data_fim
      if (filters.valor_min) params.valor_min = filters.valor_min
      if (filters.valor_max) params.valor_max = filters.valor_max
      if (filters.margem_min) params.margem_min = filters.margem_min
      if (filters.com_itens_ai) params.com_itens_ai = filters.com_itens_ai
      if (filters.viabilidade) params.viabilidade = filters.viabilidade
      params.ordenar_por = filters.ordenar_por
      params.ordem = filters.ordem

      const r = await getProcessos(params)
      setProcessos(r.data.processos || r.data || [])
      setTotal(r.data.total || 0)
    } catch (err) {
      console.error('Erro ao carregar processos:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadEditaisAprovados = async () => {
    try {
      const r = await getEditais({ status: 'aprovado', per_page: 100 })
      setEditaisDisponiveis(r.data.editais || [])
    } catch (err) {
      console.error(err)
    }
  }

  // === Handlers ===
  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    loadProcessos()
  }

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const applyFilters = () => {
    setPage(1)
    loadProcessos()
  }

  const clearFilters = () => {
    setFilters({
      busca: '', status: '', prioridade: '', cotador: '',
      data_inicio: '', data_fim: '', valor_min: '', valor_max: '',
      margem_min: '', com_itens_ai: '', viabilidade: '',
      ordenar_por: 'created_at', ordem: 'desc',
    })
    setPage(1)
    setTimeout(loadProcessos, 0)
  }

  const handleSort = (campo) => {
    setFilters(prev => ({
      ...prev,
      ordenar_por: campo,
      ordem: prev.ordenar_por === campo && prev.ordem === 'asc' ? 'desc' : 'asc'
    }))
  }

  const handleCriarProcesso = async (e) => {
    e.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      await criarProcesso({
        edital_id: parseInt(formData.edital_id),
        margem_minima: parseFloat(formData.margem_minima),
        prioridade: formData.prioridade,
        observacoes: formData.observacoes,
      })
      setShowModal(false)
      setFormData({ edital_id: '', margem_minima: '15', prioridade: 'media', observacoes: '' })
      loadProcessos()
    } catch (err) {
      setFormError(err.response?.data?.error || 'Erro ao criar processo')
    } finally {
      setSaving(false)
    }
  }

  const handleImportarItensAI = async (processoId) => {
    setAiLoading(processoId)
    setActionResult(null)
    try {
      const r = await importarItensAI(processoId)
      setActionResult({ id: processoId, tipo: 'importar', data: r.data, sucesso: true })
      loadProcessos()
    } catch (err) {
      setActionResult({ id: processoId, tipo: 'importar', erro: err.response?.data?.error || 'Erro na importação', sucesso: false })
    } finally {
      setAiLoading(null)
    }
  }

  const handleAnalisarViabilidade = async (processoId) => {
    setAiLoading(processoId)
    setActionResult(null)
    try {
      const r = await analisarViabilidade(processoId)
      setActionResult({ id: processoId, tipo: 'viabilidade', data: r.data, sucesso: true })
      loadProcessos()
    } catch (err) {
      setActionResult({ id: processoId, tipo: 'viabilidade', erro: err.response?.data?.error || 'Erro na análise', sucesso: false })
    } finally {
      setAiLoading(null)
    }
  }

  const openModal = () => {
    loadEditaisAprovados()
    setShowModal(true)
    setFormError('')
  }

  const totalPages = Math.ceil(total / perPage)

  // === Kanban groups ===
  const kanbanColumns = useMemo(() => {
    const cols = {}
    STATUS_PROCESSO.forEach(s => { cols[s.value] = { ...s, items: [] } })
    processos.forEach(p => {
      const status = p.status || 'montagem'
      if (cols[status]) cols[status].items.push(p)
    })
    return cols
  }, [processos])

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Processos</h1>
          <p className="text-gray-500">{total} processo(s) no sistema</p>
        </div>
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('table')}
              className={`p-2 ${viewMode === 'table' ? 'bg-primary-600 text-white' : 'bg-white text-gray-500 hover:bg-gray-50'}`}
              title="Tabela"
            >
              <List size={18} />
            </button>
            <button
              onClick={() => setViewMode('cards')}
              className={`p-2 ${viewMode === 'cards' ? 'bg-primary-600 text-white' : 'bg-white text-gray-500 hover:bg-gray-50'}`}
              title="Cards"
            >
              <LayoutGrid size={18} />
            </button>
            <button
              onClick={() => setViewMode('kanban')}
              className={`p-2 ${viewMode === 'kanban' ? 'bg-primary-600 text-white' : 'bg-white text-gray-500 hover:bg-gray-50'}`}
              title="Kanban"
            >
              <BarChart3 size={18} />
            </button>
          </div>
          <button onClick={openModal} className="btn-primary flex items-center gap-2">
            <Plus size={18} /> Novo Processo
          </button>
        </div>
      </div>

      {/* Barra de busca + toggle filtros */}
      <div className="card mb-4">
        <form onSubmit={handleSearch} className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={filters.busca}
                onChange={(e) => handleFilterChange('busca', e.target.value)}
                className="input-field pl-10"
                placeholder="Buscar por órgão, objeto, cotador..."
              />
            </div>
          </div>
          <button type="submit" className="btn-primary">Buscar</button>
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-secondary flex items-center gap-2 ${activeFiltersCount > 0 ? 'ring-2 ring-primary-300' : ''}`}
          >
            <SlidersHorizontal size={16} />
            Filtros
            {activeFiltersCount > 0 && (
              <span className="bg-primary-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {activeFiltersCount}
              </span>
            )}
            {showFilters ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </form>

        {/* Painel de Filtros Expandido */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {/* Status */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <Filter size={12} /> Status
                </label>
                <select
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  className="input-field text-sm"
                >
                  <option value="">Todos</option>
                  {STATUS_PROCESSO.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>

              {/* Prioridade */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <AlertTriangle size={12} /> Prioridade
                </label>
                <select
                  value={filters.prioridade}
                  onChange={(e) => handleFilterChange('prioridade', e.target.value)}
                  className="input-field text-sm"
                >
                  <option value="">Todas</option>
                  {PRIORIDADES.map(p => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </div>

              {/* Cotador */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <User size={12} /> Cotador
                </label>
                <input
                  type="text"
                  value={filters.cotador}
                  onChange={(e) => handleFilterChange('cotador', e.target.value)}
                  className="input-field text-sm"
                  placeholder="Nome do cotador"
                />
              </div>

              {/* Viabilidade */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <CheckCircle size={12} /> Viabilidade
                </label>
                <select
                  value={filters.viabilidade}
                  onChange={(e) => handleFilterChange('viabilidade', e.target.value)}
                  className="input-field text-sm"
                >
                  <option value="">Todas</option>
                  <option value="viavel">Viável</option>
                  <option value="inviavel">Inviável</option>
                  <option value="parcial">Parcialmente viável</option>
                  <option value="pendente">Não analisado</option>
                </select>
              </div>

              {/* Data início */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <Calendar size={12} /> Criado desde
                </label>
                <input
                  type="date"
                  value={filters.data_inicio}
                  onChange={(e) => handleFilterChange('data_inicio', e.target.value)}
                  className="input-field text-sm"
                />
              </div>

              {/* Data fim */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <Calendar size={12} /> Criado até
                </label>
                <input
                  type="date"
                  value={filters.data_fim}
                  onChange={(e) => handleFilterChange('data_fim', e.target.value)}
                  className="input-field text-sm"
                />
              </div>

              {/* Valor mínimo */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <DollarSign size={12} /> Valor mín (R$)
                </label>
                <input
                  type="number"
                  value={filters.valor_min}
                  onChange={(e) => handleFilterChange('valor_min', e.target.value)}
                  className="input-field text-sm"
                  placeholder="0"
                  min="0"
                />
              </div>

              {/* Valor máximo */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <DollarSign size={12} /> Valor máx (R$)
                </label>
                <input
                  type="number"
                  value={filters.valor_max}
                  onChange={(e) => handleFilterChange('valor_max', e.target.value)}
                  className="input-field text-sm"
                  placeholder="999.999"
                  min="0"
                />
              </div>

              {/* Margem mínima */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  Margem mín. (%)
                </label>
                <input
                  type="number"
                  value={filters.margem_min}
                  onChange={(e) => handleFilterChange('margem_min', e.target.value)}
                  className="input-field text-sm"
                  placeholder="0"
                  min="0"
                  step="0.5"
                />
              </div>

              {/* Itens AI importados */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <Brain size={12} /> Itens AI
                </label>
                <select
                  value={filters.com_itens_ai}
                  onChange={(e) => handleFilterChange('com_itens_ai', e.target.value)}
                  className="input-field text-sm"
                >
                  <option value="">Todos</option>
                  <option value="sim">Com itens importados</option>
                  <option value="nao">Sem itens importados</option>
                </select>
              </div>

              {/* Ordenar por */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <ArrowUpDown size={12} /> Ordenar por
                </label>
                <select
                  value={filters.ordenar_por}
                  onChange={(e) => handleFilterChange('ordenar_por', e.target.value)}
                  className="input-field text-sm"
                >
                  <option value="created_at">Data de criação</option>
                  <option value="prioridade">Prioridade</option>
                  <option value="status">Status</option>
                  <option value="margem_minima">Margem mínima</option>
                  <option value="valor_estimado">Valor estimado</option>
                  <option value="data_certame">Data do certame</option>
                </select>
              </div>

              {/* Ordem */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Ordem</label>
                <select
                  value={filters.ordem}
                  onChange={(e) => handleFilterChange('ordem', e.target.value)}
                  className="input-field text-sm"
                >
                  <option value="desc">Mais recente primeiro</option>
                  <option value="asc">Mais antigo primeiro</option>
                </select>
              </div>
            </div>

            {/* Botões filtro */}
            <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
              <button onClick={clearFilters} className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1">
                <X size={14} /> Limpar filtros
              </button>
              <button onClick={applyFilters} className="btn-primary text-sm flex items-center gap-2">
                <Filter size={14} /> Aplicar Filtros
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Resultado de ação AI */}
      {actionResult && (
        <div className={`mb-4 p-4 rounded-lg ${actionResult.sucesso ? 'bg-success-50 text-success-700' : 'bg-danger-50 text-danger-700'}`}>
          {actionResult.sucesso ? (
            <span>✅ {actionResult.tipo === 'importar' ? 'Itens importados via AI!' : 'Análise de viabilidade concluída!'}</span>
          ) : (
            <span>❌ {actionResult.erro}</span>
          )}
          <button onClick={() => setActionResult(null)} className="ml-3 underline text-sm">Fechar</button>
        </div>
      )}

      {/* === VIEWS === */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : processos.length === 0 ? (
        <div className="card text-center py-12">
          <Briefcase size={48} className="mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-600 mb-2">Nenhum processo encontrado</h3>
          <p className="text-gray-400 mb-4">Aprove editais na triagem e crie processos para cotação</p>
          <button onClick={openModal} className="btn-primary">
            <Plus size={16} className="inline mr-1" /> Criar Processo
          </button>
        </div>
      ) : viewMode === 'kanban' ? (
        /* --- KANBAN VIEW --- */
        <div className="flex gap-4 overflow-x-auto pb-4">
          {Object.values(kanbanColumns).map(col => (
            <div key={col.value} className="flex-shrink-0 w-72">
              <div className="bg-gray-100 rounded-t-lg px-3 py-2 flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-700">{col.label}</span>
                <span className="text-xs bg-white rounded-full px-2 py-0.5 text-gray-500">{col.items.length}</span>
              </div>
              <div className="bg-gray-50 rounded-b-lg p-2 space-y-2 min-h-[200px]">
                {col.items.map(p => (
                  <div key={p.id} className="bg-white rounded-lg p-3 shadow-sm border border-gray-100 hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => navigate(`/editais/${p.edital_id}`)}
                  >
                    <p className="text-sm font-medium text-gray-900 mb-1 line-clamp-2">{p.edital_orgao || `Processo #${p.id}`}</p>
                    <p className="text-xs text-gray-500 mb-2 line-clamp-1">{p.edital_objeto || '—'}</p>
                    <div className="flex items-center justify-between">
                      <StatusBadge status={p.prioridade} />
                      {p.valor_estimado && (
                        <span className="text-xs font-medium text-primary-600">{formatCurrency(p.valor_estimado)}</span>
                      )}
                    </div>
                    {p.cotador_nome && (
                      <p className="text-xs text-gray-400 mt-1.5 flex items-center gap-1">
                        <User size={10} /> {p.cotador_nome}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : viewMode === 'cards' ? (
        /* --- CARDS VIEW --- */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {processos.map(p => (
            <div key={p.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-gray-900 text-sm line-clamp-2">{p.edital_orgao || `Processo #${p.id}`}</h3>
                <StatusBadge status={p.status} />
              </div>
              <p className="text-xs text-gray-500 mb-3 line-clamp-2">{p.edital_objeto || '—'}</p>

              <div className="flex flex-wrap gap-2 mb-3 text-xs text-gray-400">
                {p.prioridade && <StatusBadge status={p.prioridade} />}
                {p.cotador_nome && <span className="flex items-center gap-1"><User size={10} /> {p.cotador_nome}</span>}
              </div>

              {p.valor_estimado && (
                <p className="text-lg font-bold text-primary-600 mb-3">{formatCurrency(p.valor_estimado)}</p>
              )}

              <div className="flex flex-wrap gap-1 text-xs text-gray-400 mb-3">
                {p.margem_minima && <span>Margem: {p.margem_minima}%</span>}
                {p.data_certame && <span>• Certame: {formatDate(p.data_certame)}</span>}
              </div>

              <div className="flex gap-2 pt-2 border-t border-gray-100">
                <button
                  onClick={() => navigate(`/editais/${p.edital_id}`)}
                  className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1"
                >
                  <Eye size={12} /> Ver Edital
                </button>
                <button
                  onClick={() => handleImportarItensAI(p.id)}
                  disabled={aiLoading === p.id}
                  className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1 disabled:opacity-50"
                >
                  {aiLoading === p.id ? <Loader2 size={12} className="animate-spin" /> : <Brain size={12} />}
                  Itens AI
                </button>
                <button
                  onClick={() => handleAnalisarViabilidade(p.id)}
                  disabled={aiLoading === p.id}
                  className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1 disabled:opacity-50"
                >
                  {aiLoading === p.id ? <Loader2 size={12} className="animate-spin" /> : <BarChart3 size={12} />}
                  Viabilidade
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* --- TABLE VIEW --- */
        <div className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <ThSortable label="ID" campo="id" current={filters} onSort={handleSort} />
                  <ThSortable label="Órgão / Objeto" campo="edital_orgao" current={filters} onSort={handleSort} />
                  <ThSortable label="Status" campo="status" current={filters} onSort={handleSort} />
                  <ThSortable label="Prioridade" campo="prioridade" current={filters} onSort={handleSort} />
                  <th className="text-left py-3 px-4 text-gray-500 font-medium">Cotador</th>
                  <ThSortable label="Margem" campo="margem_minima" current={filters} onSort={handleSort} align="right" />
                  <ThSortable label="Valor Est." campo="valor_estimado" current={filters} onSort={handleSort} align="right" />
                  <ThSortable label="Certame" campo="data_certame" current={filters} onSort={handleSort} />
                  <th className="py-3 px-4 text-gray-500 font-medium text-center">Ações</th>
                </tr>
              </thead>
              <tbody>
                {processos.map(p => (
                  <tr key={p.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 text-gray-500">{p.id}</td>
                    <td className="py-3 px-4 max-w-[280px]">
                      <p className="font-medium text-gray-900 truncate">{p.edital_orgao || `Processo #${p.id}`}</p>
                      <p className="text-xs text-gray-400 truncate">{p.edital_objeto || '—'}</p>
                    </td>
                    <td className="py-3 px-4"><StatusBadge status={p.status} /></td>
                    <td className="py-3 px-4"><StatusBadge status={p.prioridade} /></td>
                    <td className="py-3 px-4 text-gray-600">{p.cotador_nome || '—'}</td>
                    <td className="py-3 px-4 text-right font-medium text-gray-700">{p.margem_minima ? `${p.margem_minima}%` : '—'}</td>
                    <td className="py-3 px-4 text-right font-medium">{formatCurrency(p.valor_estimado)}</td>
                    <td className="py-3 px-4 text-gray-400 text-xs">{formatDate(p.data_certame)}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1 justify-center">
                        <button onClick={() => navigate(`/editais/${p.edital_id}`)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600" title="Ver edital">
                          <Eye size={15} />
                        </button>
                        <button
                          onClick={() => handleImportarItensAI(p.id)}
                          disabled={aiLoading === p.id}
                          className="p-1.5 rounded-lg hover:bg-primary-50 text-gray-400 hover:text-primary-600 disabled:opacity-50"
                          title="Importar itens via AI"
                        >
                          {aiLoading === p.id ? <Loader2 size={15} className="animate-spin" /> : <Brain size={15} />}
                        </button>
                        <button
                          onClick={() => handleAnalisarViabilidade(p.id)}
                          disabled={aiLoading === p.id}
                          className="p-1.5 rounded-lg hover:bg-green-50 text-gray-400 hover:text-green-600 disabled:opacity-50"
                          title="Análise de viabilidade"
                        >
                          {aiLoading === p.id ? <Loader2 size={15} className="animate-spin" /> : <BarChart3 size={15} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Paginação */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-t border-gray-100">
              <span className="text-sm text-gray-500">Página {page} de {totalPages} — {total} processo(s)</span>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary text-sm py-1 px-3 disabled:opacity-50">
                  <ChevronLeft size={16} />
                </button>
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn-secondary text-sm py-1 px-3 disabled:opacity-50">
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* === Modal Novo Processo === */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">Novo Processo</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>

            {formError && <div className="mb-4 p-3 bg-danger-50 text-danger-700 rounded-lg text-sm">{formError}</div>}

            <form onSubmit={handleCriarProcesso} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Edital aprovado *</label>
                <select
                  value={formData.edital_id}
                  onChange={e => setFormData({...formData, edital_id: e.target.value})}
                  className="input-field"
                  required
                >
                  <option value="">Selecione um edital...</option>
                  {editaisDisponiveis.map(e => (
                    <option key={e.id} value={e.id}>
                      #{e.id} — {e.orgao_razao_social?.substring(0, 50)} — {e.objeto_resumo?.substring(0, 40) || 'Sem descrição'}
                    </option>
                  ))}
                </select>
                {editaisDisponiveis.length === 0 && (
                  <p className="text-xs text-warning-600 mt-1">Nenhum edital aprovado disponível. Aprove editais na triagem primeiro.</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Margem mínima (%)</label>
                  <input
                    type="number"
                    value={formData.margem_minima}
                    onChange={e => setFormData({...formData, margem_minima: e.target.value})}
                    className="input-field"
                    min="0" max="100" step="0.5"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Prioridade</label>
                  <select
                    value={formData.prioridade}
                    onChange={e => setFormData({...formData, prioridade: e.target.value})}
                    className="input-field"
                  >
                    {PRIORIDADES.map(p => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
                <textarea
                  value={formData.observacoes}
                  onChange={e => setFormData({...formData, observacoes: e.target.value})}
                  className="input-field"
                  rows={3}
                  placeholder="Anotações sobre o processo..."
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={saving} className="btn-primary flex-1 disabled:opacity-50">
                  {saving ? 'Criando...' : 'Criar Processo'}
                </button>
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">Cancelar</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// === Componente auxiliar: Th com ordenação ===
function ThSortable({ label, campo, current, onSort, align = 'left' }) {
  const isActive = current.ordenar_por === campo
  return (
    <th
      className={`py-3 px-4 text-gray-500 font-medium cursor-pointer hover:text-gray-700 select-none text-${align}`}
      onClick={() => onSort(campo)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {isActive && (
          current.ordem === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />
        )}
      </span>
    </th>
  )
}
