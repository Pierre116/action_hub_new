import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'

interface User {
  id: number
  username: string
  display_name?: string
  role: string
  lang?: string
  must_change_pwd?: boolean
  leads_teams?: Array<{ id: number; name: string }>
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()
  
  // Store tokens in memory (NOT localStorage for security)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [refreshToken, setRefreshToken] = useState<string | null>(null)

  // Check for existing session on mount
  useEffect(() => {
    const storedUser = sessionStorage.getItem('user')
    const storedAccessToken = sessionStorage.getItem('access_token')
    const storedRefreshToken = sessionStorage.getItem('refresh_token')
    
    if (storedUser && storedAccessToken) {
      setUser(JSON.parse(storedUser))
      setAccessToken(storedAccessToken)
      setRefreshToken(storedRefreshToken)
    }
    setIsLoading(false)
  }, [])

  // Auto-refresh token before expiry
  useEffect(() => {
    if (!refreshToken) return

    const checkAndRefreshToken = async () => {
      try {
        const response = await api.post('/api/auth/refresh', { refresh_token: refreshToken })
        if (response.data?.data?.access_token) {
          const newAccessToken = response.data.data.access_token
          setAccessToken(newAccessToken)
          sessionStorage.setItem('access_token', newAccessToken)
        }
      } catch {
        // Refresh failed, user will need to re-login
      }
    }

    // Check every 5 minutes
    const interval = setInterval(checkAndRefreshToken, 5 * 60 * 1000)
    
    return () => clearInterval(interval)
  }, [refreshToken])

  const login = useCallback(async (username: string, password: string) => {
    setIsLoading(true)
    try {
      const response = await api.post('/api/auth/login', { username, password })
      
      if (response.data?.data) {
        const userData = response.data.data
        const newAccessToken = userData.access_token
        const newRefreshToken = userData.refresh_token

        const user: User = {
          id: userData.id,
          username: userData.username,
          display_name: userData.display_name,
          role: userData.role,
          lang: userData.lang,
          must_change_pwd: userData.must_change_pwd,
          leads_teams: userData.leads_teams || [],
        }

        setUser(user)
        setAccessToken(newAccessToken)
        setRefreshToken(newRefreshToken)

        // Store in session (not localStorage for security)
        sessionStorage.setItem('user', JSON.stringify(user))
        sessionStorage.setItem('access_token', newAccessToken)
        if (newRefreshToken) {
          sessionStorage.setItem('refresh_token', newRefreshToken)
        }

        // Redirect to change-password if must_change_pwd is set
        if (userData.must_change_pwd) {
          navigate('/change-password')
        } else {
          navigate('/')
        }
      }
    } finally {
      setIsLoading(false)
    }
  }, [navigate])

  const logout = useCallback(() => {
    // Try to logout on server (blacklist token)
    if (accessToken) {
      api.delete('/api/auth/logout', {
        headers: { Authorization: `Bearer ${accessToken}` }
      }).catch(() => {
        // Ignore errors
      })
    }

    // Clear state
    setUser(null)
    setAccessToken(null)
    setRefreshToken(null)
    sessionStorage.clear()
    
    navigate('/login')
  }, [accessToken, navigate])

  // Update API token when it changes
  useEffect(() => {
    if (accessToken) {
      api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
    } else {
      delete api.defaults.headers.common['Authorization']
    }
  }, [accessToken])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
