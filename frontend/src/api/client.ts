/**
 * API Client Configuration
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const AUTH_TOKEN_KEY = 'ai_niru_access_token'

export const getStoredToken = () => localStorage.getItem(AUTH_TOKEN_KEY)
export const setStoredToken = (token: string) => localStorage.setItem(AUTH_TOKEN_KEY, token)
export const clearStoredToken = () => localStorage.removeItem(AUTH_TOKEN_KEY)

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    const token = getStoredToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
    return Promise.reject(error)
  }
)
