import { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for existing session (both registered and guest)
    const checkAuth = async () => {
      const token = localStorage.getItem('token')
      const isGuest = localStorage.getItem('isGuest') === 'true'
      
      if (token) {
        try {
          const data = await api.getMe()
          setUser(data.user)
        } catch (error) {
          console.error('Auth check failed:', error)
          localStorage.removeItem('token')
          localStorage.removeItem('isGuest')
        }
      }
      setLoading(false)
    }

    checkAuth()
  }, [])

  const login = async (email, password) => {
    const data = await api.login(email, password)
    setUser(data.user)
    localStorage.setItem('isGuest', 'false')
    return data
  }

  const signup = async (username, email, password) => {
    const data = await api.signup(username, email, password)
    setUser(data.user)
    localStorage.setItem('isGuest', 'false')
    return data
  }

  const loginAsGuest = async () => {
    const data = await api.guestLogin()
    setUser(data.user)
    localStorage.setItem('isGuest', 'true')
    return data
  }

  const logout = () => {
    api.logout()
    setUser(null)
    localStorage.removeItem('isGuest')
  }

  const updateUser = (userData) => {
    setUser(prev => ({ ...prev, ...userData }))
  }

  const isGuestUser = () => {
    return user?.is_guest === true || localStorage.getItem('isGuest') === 'true'
  }

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      login, 
      signup, 
      loginAsGuest,
      logout,
      updateUser,
      isGuestUser
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext
