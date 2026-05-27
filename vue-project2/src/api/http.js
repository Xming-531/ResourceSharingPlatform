const DEFAULT_BASE_URL = ''

function joinUrl(baseUrl, path) {
  const b = (baseUrl || '').replace(/\/+$/, '')
  const p = (path || '').replace(/^\/+/, '')
  if (!b) return `/${p}`
  return `${b}/${p}`
}

export async function apiRequest(path, { method = 'GET', headers, body } = {}) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL
  const url = joinUrl(baseUrl, path)
  const mergedHeaders = {
    Accept: 'application/json',
    ...(body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : null),
    ...headers,
  }

  const res = await fetch(url, {
    method,
    headers: mergedHeaders,
    body: body && !(body instanceof FormData) ? JSON.stringify(body) : body,
  })

  const text = await res.text()
  const data = text ? safeJson(text) : null

  if (!res.ok) {
    const message =
      (data && (data.detail || data.message || data.error)) ||
      `${res.status} ${res.statusText}` ||
      'Request failed'
    const err = new Error(message)
    err.status = res.status
    err.data = data
    throw err
  }

  return data
}

function safeJson(text) {
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}
