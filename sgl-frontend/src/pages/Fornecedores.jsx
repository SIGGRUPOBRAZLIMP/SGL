import { useState, useEffect } from 'react'
import { getFornecedores, criarFornecedor } from '../services/api'
import { Truck, Plus, Search, X } from 'lucide-react'

export default function Fornecedores() {
  const [fornecedores, setFornecedores] = useState([])
  const [loading, setLoading] = useState(true)
  const [busca, setBusca] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({
    razao_social: '', nome_fantasia: '', cnpj: '', email: '', telefone: '', contato_nome: '', segmentos: '', observacoes: ''
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    loadFornecedores()
  }, [])

  const loadFornecedores = async (search = '') => {
    setLoading(true)
    try {
      const r = await getFornecedores(search)
      setFornecedores(r.data.fornecedores || r.data || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    loadFornecedores(busca)
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const data = {
        ...formData,
        segmentos: formData.segmentos ? formData.segmentos.split(',').map(s => s.trim()) : []
      }
      await criarFornecedor(data)
      setShowModal(false)
      setFormData({ razao_social: '', nome_fantasia: '', cnpj: '', email: '', telefone: '', contato_nome: '', segmentos: '', observacoes: '' })
      loadFornecedores()
    } catch (err) {
      setError(err.response?.data?.error || 'Erro ao salvar fornecedor')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fornecedores</h1>
          <p className="text-gray-500">{fornecedores.length} fornecedores cadastrados</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
          <Plus size={18} /> Novo Fornecedor
        </button>
      </div>

      {/* Busca */}
      <div className="card mb-6">
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="flex-1 relative">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="input-field pl-10"
              placeholder="Buscar por nome, CNPJ..."
            />
          </div>
          <button type="submit" className="btn-primary">Buscar</button>
        </form>
      </div>

      {/* Lista */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
        </div>
      ) : fornecedores.length === 0 ? (
        <div className="card text-center py-12">
          <Truck size={48} className="mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-600 mb-2">Nenhum fornecedor cadastrado</h3>
          <p className="text-gray-400">Clique em "Novo Fornecedor" para adicionar</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {fornecedores.map((f) => (
            <div key={f.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-gray-900">{f.razao_social}</h3>
                <span className={`badge ${f.ativo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {f.ativo ? 'Ativo' : 'Inativo'}
                </span>
              </div>
              {f.nome_fantasia && <p className="text-sm text-gray-500 mb-1">{f.nome_fantasia}</p>}
              {f.cnpj && <p className="text-xs text-gray-400 mb-2">CNPJ: {f.cnpj}</p>}
              {f.email && <p className="text-sm text-gray-600">{f.email}</p>}
              {f.telefone && <p className="text-sm text-gray-600">{f.telefone}</p>}
              {f.contato_nome && <p className="text-sm text-gray-500 mt-1">Contato: {f.contato_nome}</p>}
              {f.segmentos?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {f.segmentos.map((s, i) => (
                    <span key={i} className="badge bg-primary-50 text-primary-700">{s}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modal Novo Fornecedor */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">Novo Fornecedor</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>

            {error && <div className="mb-4 p-3 bg-danger-50 text-danger-700 rounded-lg text-sm">{error}</div>}

            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Razão Social *</label>
                <input type="text" required value={formData.razao_social} onChange={e => setFormData({...formData, razao_social: e.target.value})} className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome Fantasia</label>
                <input type="text" value={formData.nome_fantasia} onChange={e => setFormData({...formData, nome_fantasia: e.target.value})} className="input-field" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">CNPJ</label>
                  <input type="text" value={formData.cnpj} onChange={e => setFormData({...formData, cnpj: e.target.value})} className="input-field" placeholder="00.000.000/0000-00" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Telefone</label>
                  <input type="text" value={formData.telefone} onChange={e => setFormData({...formData, telefone: e.target.value})} className="input-field" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
                <input type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Contato (nome)</label>
                <input type="text" value={formData.contato_nome} onChange={e => setFormData({...formData, contato_nome: e.target.value})} className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Segmentos</label>
                <input type="text" value={formData.segmentos} onChange={e => setFormData({...formData, segmentos: e.target.value})} className="input-field" placeholder="informática, papelaria, limpeza" />
                <p className="text-xs text-gray-400 mt-1">Separados por vírgula</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
                <textarea value={formData.observacoes} onChange={e => setFormData({...formData, observacoes: e.target.value})} className="input-field" rows={3} />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={saving} className="btn-primary flex-1 disabled:opacity-50">
                  {saving ? 'Salvando...' : 'Salvar Fornecedor'}
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
