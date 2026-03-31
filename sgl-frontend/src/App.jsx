import { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
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
  if (loading) return (
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

    // Timeout de segurança: se travar por mais de 10s, vai para login
    const _ssoTimeout = setTimeout(() => {
      console.warn('[SSO-SIG] Timeout — redirecionando para login')
      window._ssoProcessando = false
      window.location.replace('/login?sso_erro=timeout')
    }, 10000)

    fetch('/api/auth/sso-sig', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ sso_token: ssoToken }),
    })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status} — endpoint SSO não encontrado`)
        return r.json()
      })
      .then(data => {
        clearTimeout(_ssoTimeout)
        if (data.ok) {
          localStorage.setItem('sgl_token', data.access_token)
          localStorage.setItem('sgl_user',  JSON.stringify(data.user))
          window.location.replace('/')
        } else {
          console.error('[SSO-SIG] Falha:', data.erro)
          window._ssoProcessando = false
          window.location.replace('/login?sso_erro=' + encodeURIComponent(data.erro || 'erro_sso'))
        }
      })
      .catch(e => {
        clearTimeout(_ssoTimeout)
        console.error('[SSO-SIG] Erro:', e.message)
        window._ssoProcessando = false
        window.location.replace('/login?sso_erro=' + encodeURIComponent(e.message))
      })
  }, [])

  // Mostrar loading enquanto processa o SSO
  const params   = new URLSearchParams(location.search)
  const temToken = params.get('sso_token')
  if (temToken) return (
    <div className="flex flex-col items-center justify-center h-screen gap-4">
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
