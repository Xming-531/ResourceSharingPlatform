const KEY = 'camera_platform_session_v1'

export function getSession() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setSession(session) {
  localStorage.setItem(KEY, JSON.stringify(session))
  // Same-tab reactive update hook
  window.dispatchEvent(new Event('session-changed'))
}

export function clearSession() {
  localStorage.removeItem(KEY)
  window.dispatchEvent(new Event('session-changed'))
}

export function isLoggedIn() {
  const s = getSession()
  return Boolean(s && s.token)
}

export function getRole() {
  const s = getSession()
  return s?.role || 'user'
}

export function isAdmin() {
  return getRole() === 'admin'
}

