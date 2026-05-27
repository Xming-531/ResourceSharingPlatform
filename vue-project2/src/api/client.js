import axios from 'axios'
import { getSession, clearSession } from '@/utils/session'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const s = getSession()
  if (s?.token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${s.token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err?.response?.status
    if (status === 401) {
      clearSession()
    }
    const msg = err?.response?.data?.message || err?.response?.data?.detail
    if (msg && !err.message) {
      err.message = msg
    } else if (msg) {
      err.message = msg
    }
    return Promise.reject(err)
  },
)

export function unwrap(res) {
  return res?.data
}

