import { useState, useEffect } from 'react'
import { getFiltros, criarFiltro, atualizarFiltro, deletarFiltro } from '../services/api'
import { UFS, REGIOES, MODALIDADES } from '../utils/constants'
import {
  Settings, Plus, Edit3, Trash2, X, Save, Power, PowerOff,
  MapPin, Tag, DollarSign, FileText, AlertCircle, CheckCircle,
  Copy, Search
} from 'lucide-react'

export default function Filtros() {
  const [filtros, setFiltros] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState(null)

  // Form state
  const [form, setForm] = useState({
    nome: '',
    palavras_chave: '',
    palavras_exclusao: '',
    regioes_uf: [],
    modalidades: [8],
    valor_minimo: '',
    valor_maximo: '',
    ativo: true,
  })

  useEffect(() => { loadFiltros() }, [])

  const loadFiltros = async () => {
    setLoading(true)
    try {
      const r = await getFiltros()
      setFiltros(r.data.filtros || r.data || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // === UF Selection Helpers ===
  const toggleUf = (uf) => {
    setForm(prev => ({
      ...prev,
      regioes_uf: prev.regioes_uf.includes(uf)
        ? prev.regioes_uf.filter(u => u !== uf)
        : [...prev.regioes_uf, uf]
    }))
  }

  const selectRegiao = (regiao) => {
    const ufsRegiao = REGIOES[regiao]
    setForm(prev => {
      const allSelected = ufsRegiao.every(uf => prev.regioes_uf.includes(uf))
      if (allSelected) {
        return { ...prev, regioes_uf: prev.regioes_uf.filter(uf => !ufsRegiao.includes(uf)) }
      } else {
        const newUfs = [...new Set([...prev.regioes_uf, ...ufsRegiao])]
        return { ...prev, regioes_uf: newUfs }
      }
    })
  }

  const selectAllUfs = () => setForm(prev => ({ ...prev, regioes_uf: [...UFS] }))
  const clearUfs = () => setForm(prev => ({ ...prev, regioes_uf: [] }))

  // === Modalidade Selection ===
  const toggleModalidade = (id) => {
    setForm(prev => ({
      ...prev,
      modalidades: prev.modalidades.includes(id)
        ? prev.modalidades.filter(m => m !== id)
        : [...prev.modalidades, id]
    }))
  }

  // === CRUD ===
  const openNew = () => {
    setEditingId(null)
    setForm({
      nome: '', palavras_chave: '', palavras_exclusao: '',
      regioes_uf: ['RJ', 'SP', 'MG', 'ES'], modalidades: [8],
      valor_minimo: '', valor_maximo: '', ativo: true,
    })
    setError('')
    setShowModal(true)
  }

  const openEdit = (filtro) => {
    setEditingId(filtro.id)
    setForm({
      nome: filtro.nome || '',
      palavras_chave: Array.isArray(filtro.palavras_chave) ? filtro.palavras_chave.join(', ') : (filtro.palavras_chave || ''),
      palavras_exclusao: Array.isArray(filtro.palavras_exclusao) ? filtro.palavras_exclusao.join(', ') : (filtro.palavras_exclusao || ''),
      regioes_uf: filtro.regioes_uf || [],
      modalidades: filtro.modalidades || [8],
      valor_minimo: filtro.valor_minimo || '',
      valor_maximo: filtro.valor_maximo || '',
      ativo: filtro.ativo !== false,
    })
    setError('')
    setShowModal(true)
  }

  const handleDuplicate = (filtro) => {
    setEditingId(null)
    setForm({
      nome: `${filtro.nome} (cópia)`,
      palavras_chave: Array.isArray(filtro.palavras_chave) ? filtro.palavras_chave.join(', ') : (filtro.palavras_chave || ''),
      palavras_exclusao: Array.isArray(filtro.palavras_exclusao) ? filtro.palavras_exclusao.join(', ') : (filtro.palavras_exclusao || ''),
      regioes_uf: filtro.regioes_uf || [],
      modalidades: filtro.modalidades || [8],
      valor_minimo: filtro.valor_minimo || '',
      valor_maximo: filtro.valor_maximo || '',
      ativo: true,
    })
    setError('')
    setShowModal(true)
  }

  const handleSave = async (e) => {
    e.preventDefault()
    if (!form.nome.trim()) { setError('Nome é obrigatório'); return }
    if (form.regioes_uf.length === 0) { setError('Selecione pelo menos uma UF'); return }
    if (form.modalidades.length === 0) { setError('Selecione pelo menos uma modalidade'); return }

    setSaving(true)
    setError('')

    const payload = {
      nome: form.nome.trim(),
      palavras_chave: form.palavras_chave ? form.palavras_chave.split(',').map(s => s.trim()).filter(Boolean) : [],
      palavras_exclusao: form.palavras_exclusao ? form.palavras_exclusao.split(',').map(s => s.trim()).filter(Boolean) : [],
      regioes_uf: form.regioes_uf,
      modalidades: form.modalidades,
      valor_minimo: form.valor_minimo ? parseFloat(form.valor_minimo) : null,
      valor_maximo: form.valor_maximo ? parseFloat(form.valor_maximo) : null,
      ativo: form.ativo,
    }

    try {
      if (editingId) {
        await atualizarFiltro(editingId, payload)
      } else {
        await criarFiltro(payload)
      }
      setShowModal(false)
      loadFiltros()
    } catch (err) {
      setError(err.response?.data?.error || 'Erro ao salvar filtro')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await deletarFiltro(id)
      setDeleteConfirm(null)
      loadFiltros()
    } catch (err) {
      console.error(err)
    }
  }

  const handleToggleAtivo = async (filtro) => {
    try {
      await atualizarFiltro(filtro.id, { ...filtro, ativo: !filtro.ativo })
      loadFiltros()
    } catch (err) {
      console.error(err)
    }
  }

  // Check region selection state
  const isRegiaoSelected = (regiao) => {
    const ufs = REGIOES[regiao]
    const selected = ufs.filter(uf => form.regioes_uf.includes(uf)).length
    if (selected === ufs.length) return 'all'
    if (selected > 0) return 'partial'
    return 'none'
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Filtros de Prospecção</h1>
          <p className="text-gray-500">Configure filtros para captar editais automaticamente</p>
        </div>
        <button onClick={openNew} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> Novo Filtro
        </button>
      </div>

      {/* Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-sm text-blue-700 flex items-start gap-3">
        <AlertCircle size={18} className="flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-medium">Como funcionam os filtros?</p>
          <p className="mt-1 text-blue-600">
            Cada filtro define critérios de busca para a captação automática. Quando você executa uma captação,
            o sistema usa os filtros <strong>ativos</strong> para buscar editais no PNCP que correspondam às
            palavras-chave, UFs, modalidades e faixa de valor configurados.
          </p>
        </div>
      </div>

      {/* Lista de filtros */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : filtros.length === 0 ? (
        <div className="card text-center py-12">
          <Settings size={48} className="mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-600 mb-2">Nenhum filtro configurado</h3>
          <p className="text-gray-400 mb-4">Crie filtros para automatizar a busca de editais</p>
          <button onClick={openNew} className="btn-primary"><Plus size={16} className="inline mr-1" /> Criar Primeiro Filtro</button>
        </div>
      ) : (
        <div className="space-y-4">
          {filtros.map(f => (
            <div key={f.id} className={`card hover:shadow-md transition-shadow ${!f.ativo ? 'opacity-60' : ''}`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold text-gray-900">{f.nome}</h3>
                    <span className={`badge ${f.ativo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {f.ativo ? 'Ativo' : 'Inativo'}
                    </span>
                  </div>

                  {/* Palavras-chave */}
                  {f.palavras_chave?.length > 0 && (
                    <div className="flex items-start gap-2 mb-2">
                      <Tag size={14} className="text-green-500 flex-shrink-0 mt-0.5" />
                      <div className="flex flex-wrap gap-1">
                        {(Array.isArray(f.palavras_chave) ? f.palavras_chave : []).map((p, i) => (
                          <span key={i} className="badge bg-green-50 text-green-700 text-xs">{p}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Palavras de exclusão */}
                  {f.palavras_exclusao?.length > 0 && (
                    <div className="flex items-start gap-2 mb-2">
                      <X size={14} className="text-red-400 flex-shrink-0 mt-0.5" />
                      <div className="flex flex-wrap gap-1">
                        {(Array.isArray(f.palavras_exclusao) ? f.palavras_exclusao : []).map((p, i) => (
                          <span key={i} className="badge bg-red-50 text-red-600 text-xs line-through">{p}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* UFs */}
                  {f.regioes_uf?.length > 0 && (
                    <div className="flex items-start gap-2 mb-2">
                      <MapPin size={14} className="text-blue-500 flex-shrink-0 mt-0.5" />
                      <div className="flex flex-wrap gap-1">
                        {f.regioes_uf.map((uf, i) => (
                          <span key={i} className="badge bg-blue-50 text-blue-700 text-xs">{uf}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Modalidades */}
                  {f.modalidades?.length > 0 && (
                    <div className="flex items-start gap-2 mb-2">
                      <FileText size={14} className="text-purple-500 flex-shrink-0 mt-0.5" />
                      <div className="flex flex-wrap gap-1">
                        {f.modalidades.map((mId, i) => {
                          const mod = MODALIDADES.find(m => m.id === mId)
                          return <span key={i} className="badge bg-purple-50 text-purple-700 text-xs">{mod?.nome || `Mod. ${mId}`}</span>
                        })}
                      </div>
                    </div>
                  )}

                  {/* Faixa de valor */}
                  {(f.valor_minimo || f.valor_maximo) && (
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <DollarSign size={14} className="text-orange-500" />
                      <span>
                        {f.valor_minimo ? `R$ ${Number(f.valor_minimo).toLocaleString('pt-BR')}` : 'R$ 0'}
                        {' — '}
                        {f.valor_maximo ? `R$ ${Number(f.valor_maximo).toLocaleString('pt-BR')}` : 'Sem limite'}
                      </span>
                    </div>
                  )}
                </div>

                {/* Ações */}
                <div className="flex flex-col gap-1 ml-4">
                  <button
                    onClick={() => handleToggleAtivo(f)}
                    className={`p-1.5 rounded-lg ${f.ativo ? 'hover:bg-orange-50 text-orange-500' : 'hover:bg-green-50 text-green-500'}`}
                    title={f.ativo ? 'Desativar' : 'Ativar'}
                  >
                    {f.ativo ? <PowerOff size={16} /> : <Power size={16} />}
                  </button>
                  <button onClick={() => openEdit(f)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500" title="Editar">
                    <Edit3 size={16} />
                  </button>
                  <button onClick={() => handleDuplicate(f)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400" title="Duplicar">
                    <Copy size={16} />
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(f.id)}
                    className="p-1.5 rounded-lg hover:bg-red-50 text-red-400"
                    title="Excluir"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {/* Confirmação de delete */}
              {deleteConfirm === f.id && (
                <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between bg-red-50 -mx-5 -mb-5 px-5 py-3 rounded-b-xl">
                  <span className="text-sm text-red-700">Confirma excluir "{f.nome}"?</span>
                  <div className="flex gap-2">
                    <button onClick={() => handleDelete(f.id)} className="btn-danger text-xs py-1 px-3">Sim, excluir</button>
                    <button onClick={() => setDeleteConfirm(null)} className="btn-secondary text-xs py-1 px-3">Cancelar</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* === MODAL Criar/Editar Filtro === */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">
                {editingId ? 'Editar Filtro' : 'Novo Filtro de Prospecção'}
              </h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>

            {error && <div className="mb-4 p-3 bg-danger-50 text-danger-700 rounded-lg text-sm">{error}</div>}

            <form onSubmit={handleSave} className="space-y-5">
              {/* Nome */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do filtro *</label>
                <input
                  type="text"
                  value={form.nome}
                  onChange={e => setForm({...form, nome: e.target.value})}
                  className="input-field"
                  placeholder="Ex: Material de Escritório - Sudeste"
                  required
                />
              </div>

              {/* Palavras-chave */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  <Tag size={14} className="text-green-500" /> Palavras-chave (inclusão)
                </label>
                <textarea
                  value={form.palavras_chave}
                  onChange={e => setForm({...form, palavras_chave: e.target.value})}
                  className="input-field"
                  rows={2}
                  placeholder="material de escritório, papelaria, toner, cartucho, papel A4"
                />
                <p className="text-xs text-gray-400 mt-1">Separadas por vírgula. Editais que contenham qualquer uma dessas palavras serão captados.</p>
              </div>

              {/* Palavras de exclusão */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  <X size={14} className="text-red-400" /> Palavras de exclusão
                </label>
                <textarea
                  value={form.palavras_exclusao}
                  onChange={e => setForm({...form, palavras_exclusao: e.target.value})}
                  className="input-field"
                  rows={2}
                  placeholder="construção, obra, reforma, engenharia"
                />
                <p className="text-xs text-gray-400 mt-1">Separadas por vírgula. Editais que contenham essas palavras serão ignorados.</p>
              </div>

              {/* Modalidades */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Modalidades</label>
                <div className="flex flex-wrap gap-2">
                  {MODALIDADES.map(m => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => toggleModalidade(m.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        form.modalidades.includes(m.id) ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {m.nome}
                    </button>
                  ))}
                </div>
              </div>

              {/* UFs por Região */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700 flex items-center gap-1">
                    <MapPin size={14} className="text-blue-500" /> Estados (UF)
                  </label>
                  <div className="flex gap-1">
                    {Object.keys(REGIOES).map(regiao => {
                      const state = isRegiaoSelected(regiao)
                      return (
                        <button
                          key={regiao}
                          type="button"
                          onClick={() => selectRegiao(regiao)}
                          className={`text-xs px-2 py-1 rounded-lg font-medium transition-colors ${
                            state === 'all' ? 'bg-primary-600 text-white' :
                            state === 'partial' ? 'bg-primary-200 text-primary-800' :
                            'bg-gray-100 text-gray-600 hover:bg-gray-200'
                          }`}
                        >
                          {regiao}
                        </button>
                      )
                    })}
                    <button type="button" onClick={selectAllUfs} className="text-xs px-2 py-1 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 font-medium">
                      Todos
                    </button>
                    <button type="button" onClick={clearUfs} className="text-xs px-2 py-1 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 font-medium">
                      Limpar
                    </button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {UFS.map(uf => (
                    <button
                      key={uf}
                      type="button"
                      onClick={() => toggleUf(uf)}
                      className={`w-10 h-8 rounded-lg text-xs font-medium transition-colors ${
                        form.regioes_uf.includes(uf) ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                      }`}
                    >
                      {uf}
                    </button>
                  ))}
                </div>
                {form.regioes_uf.length > 0 && (
                  <p className="text-xs text-gray-400 mt-1.5">{form.regioes_uf.length} estado(s): {form.regioes_uf.join(', ')}</p>
                )}
              </div>

              {/* Faixa de valor */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                  <DollarSign size={14} className="text-orange-500" /> Faixa de valor estimado
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Valor mínimo (R$)</label>
                    <input
                      type="number"
                      value={form.valor_minimo}
                      onChange={e => setForm({...form, valor_minimo: e.target.value})}
                      className="input-field"
                      placeholder="5.000"
                      min="0"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Valor máximo (R$)</label>
                    <input
                      type="number"
                      value={form.valor_maximo}
                      onChange={e => setForm({...form, valor_maximo: e.target.value})}
                      className="input-field"
                      placeholder="5.000.000"
                      min="0"
                    />
                  </div>
                </div>
              </div>

              {/* Ativo */}
              <div className="flex items-center gap-3">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.ativo}
                    onChange={e => setForm({...form, ativo: e.target.checked})}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 rounded-full peer-checked:bg-primary-600 peer-focus:ring-2 peer-focus:ring-primary-300 transition-colors after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                </label>
                <span className="text-sm text-gray-700">Filtro ativo</span>
              </div>

              {/* Botões */}
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50">
                  {saving ? 'Salvando...' : <><Save size={16} /> {editingId ? 'Atualizar Filtro' : 'Criar Filtro'}</>}
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
