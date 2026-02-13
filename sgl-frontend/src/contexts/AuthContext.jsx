import { createContext, useContext, useState, useEffect } from 'react'
import { login as apiLogin } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const savedUser = localStorage.getItem('sgl_user')
    const savedToken = localStorage.getItem('sgl_token')
    if (savedUser && savedToken) {
      setUser(JSON.parse(savedUser))
    }
    setLoading(false)
  }, [])

  const login = async (email, senha) => {
    const response = await apiLogin(email, senha)
    const { access_token, usuario } = response.data
    localStorage.setItem('sgl_token', access_token)
    localStorage.setItem('sgl_user', JSON.stringify(usuario))
    setUser(usuario)
    return usuario
  }

  const logout = () => {
    localStorage.removeItem('sgl_token')
    localStorage.removeItem('sgl_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
