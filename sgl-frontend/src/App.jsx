import { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import api from './services/api'
import { useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Editais from './pages/Editais'
import EditalDetalhe from './pages/EditalDetalhe'
import Triagem from './pages/Triagem'
import Captacao from './pages/Captacao'
import Fornecedores from './pages/Fornecedores'
import Processos from './pages/Processos'
import Filtros from './pages/Filtros'

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  // Se há sso_token na URL, o SSO ainda está processando — não redirecionar para login
  const params = new URLSearchParams(location.search)
  const temSsoToken = params.get('sso_token')

  if (loading || temSsoToken) return (
    <div className="flex items-center justify-center h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>
  )
  return user ? children : <Navigate to="/login" />
}

// ── SSO: Intercepta ?sso_token= vindo do SIG ──────────────────────────────
function SSOHandler() {
  const location = useLocation()

  useEffect(() => {
    const params    = new URLSearchParams(location.search)
    const ssoToken  = params.get('sso_token')
    if (!ssoToken) return

    // Já está processando — evitar chamada dupla
    if (window._ssoProcessando) return
    window._ssoProcessando = true

    // Timeout aumentado para 30s — Render pode ter cold start lento
    const _ssoTimeout = setTimeout(() => {
      console.warn('[SSO-SIG] Timeout — redirecionando para login')
      window._ssoProcessando = false
      window.location.replace('/login?sso_erro=timeout')
    }, 30000)

    // Usa o api (axios) que já tem a URL correta do backend (sgl-api-xm64.onrender.com)
    api.post('/auth/sso-sig', { sso_token: ssoToken })
      .then(response => {
        clearTimeout(_ssoTimeout)
        const data = response.data
        if (data.ok) {
          localStorage.setItem('sgl_token', data.access_token)
          localStorage.setItem('sgl_user',  JSON.stringify(data.user))
          // Remove sso_token da URL antes de redirecionar
          window.location.replace('/')
        } else {
          console.error('[SSO-SIG] Falha:', data.erro)
          window._ssoProcessando = false
          window.location.replace('/login?sso_erro=' + encodeURIComponent(data.erro || 'erro_sso'))
        }
      })
      .catch(e => {
        clearTimeout(_ssoTimeout)
        const msg = e.response?.data?.erro || e.message || 'erro_rede'
        console.error('[SSO-SIG] Erro:', msg)
        window._ssoProcessando = false
        window.location.replace('/login?sso_erro=' + encodeURIComponent(msg))
      })
  }, [])

  // Enquanto o SSO processa, mostrar loading fullscreen e NÃO renderizar as Routes
  const params   = new URLSearchParams(location.search)
  const temToken = params.get('sso_token')
  if (temToken) return (
    <div className="flex flex-col items-center justify-center h-screen gap-4"
         style={{ position: 'fixed', inset: 0, background: 'white', zIndex: 9999 }}>
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      <p className="text-gray-500 text-sm">Autenticando via SIG...</p>
    </div>
  )

  return null
}
// ──────────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <>
      <SSOHandler />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="editais" element={<Editais />} />
          <Route path="editais/:id" element={<EditalDetalhe />} />
          <Route path="triagem" element={<Triagem />} />
          <Route path="captacao" element={<Captacao />} />
          <Route path="processos" element={<Processos />} />
          <Route path="fornecedores" element={<Fornecedores />} />
          <Route path="filtros" element={<Filtros />} />
        </Route>
      </Routes>
    </>
  )
}
