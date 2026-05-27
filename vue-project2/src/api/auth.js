import { api, unwrap } from '@/api/client'

export async function login({ username, password }) {
  // Django: POST /api/auth/login { username, password }
  return unwrap(await api.post('/api/auth/login', { username, password }))
}

export async function register({ username, phone, password }) {
  // Django: POST /api/auth/register { username, password, phone }
  return unwrap(await api.post('/api/auth/register', { username, phone, password }))
}

export async function logout() {
  return unwrap(await api.post('/api/auth/logout'))
}

/** 公开接口：管理员联系电话（用于登录页提示等，随后台用户表变化） */
export async function fetchAdminSupportPhone() {
  return unwrap(await api.get('/api/public/admin-support-phone'))
}

/** 普通用户注销本人账户（DELETE） */
export async function deleteMyAccount() {
  return unwrap(await api.delete('/api/me/account'))
}

