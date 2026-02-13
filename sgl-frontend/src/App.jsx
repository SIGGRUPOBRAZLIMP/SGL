import { Routes, Route, Navigate } from 'react-router-dom'
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

export default function App() {
  return (
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
  )
}
