import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' }
})

// Interceptor para adicionar token JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('sgl_token')
  if (token) {
    config.headers.Authorization = Bearer 
  }
  return config
})

// Interceptor para tratar 401 (token expirado)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('sgl_token')
      localStorage.removeItem('sgl_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ========== Auth ==========
export const login = (email, senha) => api.post('/auth/login', { email, senha })

// ========== Dashboard ==========
export const getDashboardStats = () => api.get('/dashboard/stats')

// ========== Editais ==========
export const getEditais = (params) => api.get('/editais', { params })
export const getEdital = (id) => api.get(/editais/)
export const captarEditais = (data) => api.post('/editais/captar', data)

// ========== AI (Claude) ==========
export const extrairItensAI = (id) => api.post(/editais//extrair-itens)
export const classificarEdital = (id, segmentos) => api.post(/editais//classificar, { segmentos })
export const resumirEdital = (id) => api.post(/editais//resumir)

// ========== Triagem ==========
export const getTriagem = (status = 'pendente') => api.get('/triagem', { params: { status } })
export const decidirTriagem = (editalId, data) => api.put(/triagem/, data)

// ========== Filtros de Prospeccao ==========
export const getFiltros = () => api.get('/filtros')
export const criarFiltro = (data) => api.post('/filtros', data)
export const atualizarFiltro = (id, data) => api.put(/filtros/, data)
export const deletarFiltro = (id) => api.delete(/filtros/)

// ========== Fornecedores ==========
export const getFornecedores = (busca) => api.get('/fornecedores', { params: { busca } })
export const criarFornecedor = (data) => api.post('/fornecedores', data)
export const atualizarFornecedor = (id, data) => api.put(/fornecedores/, data)
export const deletarFornecedor = (id) => api.delete(/fornecedores/)

// ========== Processos ==========
export const getProcessos = (params) => api.get('/processos', { params })
export const getProcesso = (id) => api.get(/processos/)
export const criarProcesso = (data) => api.post('/processos', data)
export const atualizarProcesso = (id, data) => api.put(/processos/, data)
export const importarItensAI = (processoId) => api.post(/processos//importar-itens-ai)
export const analisarViabilidade = (processoId) => api.post(/processos//analisar-viabilidade)

export default api
