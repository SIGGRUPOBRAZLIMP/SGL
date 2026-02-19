import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { getEditais } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import { STATUS_EDITAL, MODALIDADES, UFS, REGIOES, formatCurrency, formatDate } from '../utils/constants'
import {
  FileText, Search, ChevronLeft, ChevronRight, ExternalLink,
  SlidersHorizontal, X, Filter, Calendar, DollarSign,
  MapPin, ChevronDown, ChevronUp, ArrowUpDown, Download
} from 'lucide-react'

export default function Editais() {
  const [editais, setEditais] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const navigate = useNavigate()
  const perPage = 15

  // --- Filtros ---
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({
    busca: '',
    status: '',
    modalidade: '',
    uf: '',
    municipio: '',
    srp: '',
    data_pub_inicio: '',
    data_pub_fim: '',
    data_certame_inicio: '',
    data_certame_fim: '',
    valor_min: '',
    valor_max: '',
    com_arquivos: '',
    com_itens_ai: '',
    ordenar_por: 'data_publicacao',
    ordem: 'desc',
  })

  const activeFiltersCount = useMemo(() => {
    return Object.entries(filters).filter(([key, val]) =>
      val !== '' && !['ordenar_por', 'ordem', 'busca'].includes(key)
    ).length
  }, [filters])

  useEffect(() => { loadEditais() }, [page, filters.ordenar_por, filters.ordem])

  const loadEditais = async () => {
    setLoading(true)
    try {
      const params = { page, per_page: perPage }
      if (filters.busca) params.busca = filters.busca
      if (filters.status) params.status = filters.status
      if (filters.modalidade) params.modalidade = filters.modalidade
      if (filters.uf) params.uf = filters.uf
      if (filters.municipio) params.municipio = filters.municipio
      if (filters.srp) params.srp = filters.srp
      if (filters.data_pub_inicio) params.data_pub_inicio = filters.data_pub_inicio
      if (filters.data_pub_fim) params.data_pub_fim = filters.data_pub_fim
      if (filters.data_certame_inicio) params.data_certame_inicio = filters.data_certame_inicio
      if (filters.data_certame_fim) params.data_certame_fim = filters.data_certame_fim
      if (filters.valor_min) params.valor_min = filters.valor_min
      if (filters.valor_max) params.valor_max = filters.valor_max
      if (filters.com_arquivos) params.com_arquivos = filters.com_arquivos
      if (filters.com_itens_ai) params.com_itens_ai = filters.com_itens_ai
      params.ordenar_por = filters.ordenar_por
      params.ordem = filters.ordem

      const r = await getEditais(params)
      setEditais(r.data.editais || [])
      setTotal(r.data.total || 0)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    loadEditais()
  }

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const applyFilters = () => { setPage(1); loadEditais() }

  const clearFilters = () => {
    setFilters({
      busca: '', status: '', modalidade: '', uf: '', municipio: '', srp: '',
      data_pub_inicio: '', data_pub_fim: '', data_certame_inicio: '', data_certame_fim: '',
      valor_min: '', valor_max: '', com_arquivos: '', com_itens_ai: '',
      ordenar_por: 'data_publicacao', ordem: 'desc',
    })
    setPage(1)
    setTimeout(loadEditais, 0)
  }

  const handleSort = (campo) => {
    setFilters(prev => ({
      ...prev,
      ordenar_por: campo,
      ordem: prev.ordenar_por === campo && prev.ordem === 'asc' ? 'desc' : 'asc'
    }))
  }

  const totalPages = Math.ceil(total / perPage)

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Editais</h1>
          <p className="text-gray-500">{total} edital(is) no sistema</p>
        </div>
      </div>

      {/* Busca + toggle filtros */}
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
                placeholder="Órgão, objeto, número PNCP..."
              />
            </div>
          </div>

          {/* Quick filters inline */}
          <div className="w-36">
            <select value={filters.status} onChange={(e) => { handleFilterChange('status', e.target.value); setPage(1); setTimeout(loadEditais, 0) }} className="input-field text-sm">
              <option value="">Status</option>
              {STATUS_EDITAL.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
          <div className="w-36">
            <select value={filters.uf} onChange={(e) => { handleFilterChange('uf', e.target.value); setPage(1); setTimeout(loadEditais, 0) }} className="input-field text-sm">
              <option value="">UF</option>
              {UFS.map(uf => <option key={uf} value={uf}>{uf}</option>)}
            </select>
          </div>

          <button type="submit" className="btn-primary">Buscar</button>
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-secondary flex items-center gap-2 ${activeFiltersCount > 0 ? 'ring-2 ring-primary-300' : ''}`}
          >
            <SlidersHorizontal size={16} />
            Mais Filtros
            {activeFiltersCount > 0 && (
              <span className="bg-primary-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {activeFiltersCount}
              </span>
            )}
            {showFilters ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </form>

        {/* Painel de filtros expandido */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">

              {/* Modalidade */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Modalidade</label>
                <select value={filters.modalidade} onChange={(e) => handleFilterChange('modalidade', e.target.value)} className="input-field text-sm">
                  <option value="">Todas</option>
                  {MODALIDADES.map(m => <option key={m.id} value={m.nome}>{m.nome}</option>)}
                </select>
              </div>

              {/* Município */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Município</label>
                <input
                  type="text"
                  value={filters.municipio}
                  onChange={(e) => handleFilterChange('municipio', e.target.value)}
                  className="input-field text-sm"
                  placeholder="Nome do município"
                />
              </div>

              {/* SRP */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">SRP (Registro de Preço)</label>
                <select value={filters.srp} onChange={(e) => handleFilterChange('srp', e.target.value)} className="input-field text-sm">
                  <option value="">Todos</option>
                  <option value="sim">Sim (SRP)</option>
                  <option value="nao">Não</option>
                </select>
              </div>

              {/* Data publicação início */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <Calendar size={12} /> Publicado desde
                </label>
                <input type="date" value={filters.data_pub_inicio} onChange={(e) => handleFilterChange('data_pub_inicio', e.target.value)} className="input-field text-sm" />
              </div>

              {/* Data publicação fim */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <Calendar size={12} /> Publicado até
                </label>
                <input type="date" value={filters.data_pub_fim} onChange={(e) => handleFilterChange('data_pub_fim', e.target.value)} className="input-field text-sm" />
              </div>

              {/* Data certame início */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <Calendar size={12} /> Certame desde
                </label>
                <input type="date" value={filters.data_certame_inicio} onChange={(e) => handleFilterChange('data_certame_inicio', e.target.value)} className="input-field text-sm" />
              </div>

              {/* Data certame fim */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <Calendar size={12} /> Certame até
                </label>
                <input type="date" value={filters.data_certame_fim} onChange={(e) => handleFilterChange('data_certame_fim', e.target.value)} className="input-field text-sm" />
              </div>

              {/* Valor mín */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <DollarSign size={12} /> Valor mín (R$)
                </label>
                <input type="number" value={filters.valor_min} onChange={(e) => handleFilterChange('valor_min', e.target.value)} className="input-field text-sm" placeholder="0" min="0" />
              </div>

              {/* Valor máx */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <DollarSign size={12} /> Valor máx (R$)
                </label>
                <input type="number" value={filters.valor_max} onChange={(e) => handleFilterChange('valor_max', e.target.value)} className="input-field text-sm" placeholder="999.999" min="0" />
              </div>

              {/* Com arquivos */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Arquivos</label>
                <select value={filters.com_arquivos} onChange={(e) => handleFilterChange('com_arquivos', e.target.value)} className="input-field text-sm">
                  <option value="">Todos</option>
                  <option value="sim">Com arquivos</option>
                  <option value="nao">Sem arquivos</option>
                </select>
              </div>

              {/* Com itens AI */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Itens AI extraídos</label>
                <select value={filters.com_itens_ai} onChange={(e) => handleFilterChange('com_itens_ai', e.target.value)} className="input-field text-sm">
                  <option value="">Todos</option>
                  <option value="sim">Com itens extraídos</option>
                  <option value="nao">Sem itens extraídos</option>
                </select>
              </div>

              {/* Ordenar por */}
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                  <ArrowUpDown size={12} /> Ordenar por
                </label>
                <select value={filters.ordenar_por} onChange={(e) => handleFilterChange('ordenar_por', e.target.value)} className="input-field text-sm">
                  <option value="data_publicacao">Data de publicação</option>
                  <option value="data_certame">Data do certame</option>
                  <option value="valor_estimado">Valor estimado</option>
                  <option value="orgao_razao_social">Órgão (A-Z)</option>
                  <option value="status">Status</option>
                  <option value="created_at">Data de captação</option>
                </select>
              </div>
            </div>

            {/* Botões */}
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

      {/* Tabela */}
      <div className="card overflow-hidden p-0">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
          </div>
        ) : editais.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <FileText size={48} className="mx-auto mb-3 opacity-50" />
            <p>Nenhum edital encontrado</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <ThSort label="ID" campo="id" current={filters} onSort={handleSort} />
                  <ThSort label="Órgão" campo="orgao_razao_social" current={filters} onSort={handleSort} />
                  <th className="text-left py-3 px-4 text-gray-500 font-medium">Objeto</th>
                  <th className="text-left py-3 px-4 text-gray-500 font-medium">UF</th>
                  <th className="text-left py-3 px-4 text-gray-500 font-medium">Modalidade</th>
                  <ThSort label="Valor Est." campo="valor_estimado" current={filters} onSort={handleSort} align="right" />
                  <ThSort label="Status" campo="status" current={filters} onSort={handleSort} />
                  <ThSort label="Publicação" campo="data_publicacao" current={filters} onSort={handleSort} />
                  <ThSort label="Certame" campo="data_certame" current={filters} onSort={handleSort} />
                  <th className="py-3 px-4"></th>
                </tr>
              </thead>
              <tbody>
                {editais.map((e) => (
                  <tr key={e.id} className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer" onClick={() => navigate(`/editais/${e.id}`)}>
                    <td className="py-3 px-4 text-gray-500">{e.id}</td>
                    <td className="py-3 px-4 font-medium text-gray-900 max-w-[200px] truncate">{e.orgao_razao_social}</td>
                    <td className="py-3 px-4 text-gray-600 max-w-[250px] truncate">{e.objeto_resumo || '—'}</td>
                    <td className="py-3 px-4 text-gray-600">{e.uf || '—'}</td>
                    <td className="py-3 px-4 text-gray-600 text-xs">{e.modalidade_nome || '—'}</td>
                    <td className="py-3 px-4 text-right font-medium">{formatCurrency(e.valor_estimado)}</td>
                    <td className="py-3 px-4"><StatusBadge status={e.status} /></td>
                    <td className="py-3 px-4 text-gray-400 text-xs">{formatDate(e.data_publicacao)}</td>
                    <td className="py-3 px-4 text-gray-400 text-xs">{formatDate(e.data_certame)}</td>
                    <td className="py-3 px-4">
                      <ExternalLink size={16} className="text-gray-400" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginação */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-t border-gray-100">
            <span className="text-sm text-gray-500">Página {page} de {totalPages} — {total} edital(is)</span>
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
    </div>
  )
}

function ThSort({ label, campo, current, onSort, align = 'left' }) {
  const isActive = current.ordenar_por === campo
  return (
    <th className={`py-3 px-4 text-gray-500 font-medium cursor-pointer hover:text-gray-700 select-none text-${align}`} onClick={() => onSort(campo)}>
      <span className="inline-flex items-center gap-1">
        {label}
        {isActive && (current.ordem === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
      </span>
    </th>
  )
}
