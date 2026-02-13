import axios from 'axios'

const API_URL = window.location.hostname.includes('onrender.com') ? 'https://sgl-api-xm64.onrender.com/api' : '/api'

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('sgl_token')
  if (token) { config.headers.Authorization = 'Bearer ' + token }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('sgl_token')
      localStorage.removeItem('sgl_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const login = (email, senha) => api.post('/auth/login', { email, senha })
export const getDashboardStats = () => api.get('/dashboard/stats')
export const getEditais = (params) => api.get('/editais', { params })
export const getEdital = (id) => api.get('/editais/' + id)
export const captarEditais = (data) => api.post('/editais/captar', data)
export const extrairItensAI = (id) => api.post('/editais/' + id + '/extrair-itens')
export const classificarEdital = (id, segmentos) => api.post('/editais/' + id + '/classificar', { segmentos })
export const resumirEdital = (id) => api.post('/editais/' + id + '/resumir')
export const getTriagem = (status) => api.get('/triagem', { params: { status: status || 'pendente' } })
export const decidirTriagem = (editalId, data) => api.put('/triagem/' + editalId, data)
export const getFiltros = () => api.get('/filtros')
export const criarFiltro = (data) => api.post('/filtros', data)
export const atualizarFiltro = (id, data) => api.put('/filtros/' + id, data)
export const deletarFiltro = (id) => api.delete('/filtros/' + id)
export const getFornecedores = (busca) => api.get('/fornecedores', { params: { busca } })
export const criarFornecedor = (data) => api.post('/fornecedores', data)
export const atualizarFornecedor = (id, data) => api.put('/fornecedores/' + id, data)
export const deletarFornecedor = (id) => api.delete('/fornecedores/' + id)
export const getProcessos = (params) => api.get('/processos', { params })
export const getProcesso = (id) => api.get('/processos/' + id)
export const criarProcesso = (data) => api.post('/processos', data)
export const atualizarProcesso = (id, data) => api.put('/processos/' + id, data)
export const importarItensAI = (pid) => api.post('/processos/' + pid + '/importar-itens-ai')
export const analisarViabilidade = (pid) => api.post('/processos/' + pid + '/analisar-viabilidade')
export default api
