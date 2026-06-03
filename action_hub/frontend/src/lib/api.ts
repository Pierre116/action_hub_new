import axios, { AxiosError, AxiosResponse } from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Store refresh token in memory
let refreshTokenPromise: Promise<string | null> | null = null

// Response interceptor: handle 401 and token refresh
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config
    const originalHeaders = originalRequest?.headers as Record<string, string | boolean> | undefined
    
    // If 401 and haven't tried to refresh yet
    if (error.response?.status === 401 && originalRequest && originalHeaders && !originalHeaders['_retry']) {
      originalHeaders['_retry'] = true
      
      const refreshToken = sessionStorage.getItem('refresh_token')
      
      if (refreshToken && !refreshTokenPromise) {
        // Create refresh promise to prevent multiple refresh requests
        refreshTokenPromise = (async () => {
          try {
            const response = await axios.post('/api/auth/refresh', { refresh_token: refreshToken })
            if (response.data?.data?.access_token) {
              const newAccessToken = response.data.data.access_token
              sessionStorage.setItem('access_token', newAccessToken)
              return newAccessToken
            }
            return null
          } catch {
            return null
          } finally {
            refreshTokenPromise = null
          }
        })()
      }
      
      const newToken = await refreshTokenPromise
      
      if (newToken) {
        // Retry original request with new token
        originalHeaders['Authorization'] = `Bearer ${newToken}`
        return api(originalRequest)
      }
      
      // Refresh failed, redirect to login
      sessionStorage.clear()
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

// Request interceptor: inject Bearer token
api.interceptors.request.use(
  (config) => {
    const token = sessionStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

export default api
