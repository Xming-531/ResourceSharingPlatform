import { api, unwrap } from '@/api/client'

export async function adminDashboardStats() {
  return unwrap(await api.get('/api/admin/dashboard-stats'))
}

export async function adminListUsers() {
  const res = unwrap(await api.get('/api/admin/users'))
  const list = res?.data || []
  return {
    ...res,
    data: list.map((u) => ({
      id: String(u.id),
      username: u.username,
      phone: u.phone,
      role: String(u.role) === '0' ? 'admin' : 'user',
      enabled: Number(u.status) === 1,
      raw: u,
    })),
  }
}

export async function adminDisableUser(id, enabled) {
  // Django endpoint: POST /api/admin/users/<id>/disable { disabled: true/false }
  return unwrap(await api.post(`/api/admin/users/${id}/disable`, { disabled: !enabled }))
}

export async function adminDeleteUser(id) {
  return unwrap(await api.delete(`/api/admin/users/${id}`))
}

/** 将用户密码重置为 123，并清除其登录 Token */
export async function adminResetUserPassword(id) {
  return unwrap(await api.post(`/api/admin/users/${id}/reset-password`, {}))
}

export async function adminListProducts(params = {}) {
  const res = unwrap(
    await api.get('/api/admin/equipments', {
      params: {
        ...(params.status ? { status: params.status } : {}),
      },
    }),
  )
  const list = res?.data || []
  return {
    ...res,
    data: list.map((eq) => ({
      id: String(eq.equipment_id),
      title: eq.title,
      owner: eq.owner?.username || String(eq.owner_id),
      status: eq.status,
      raw: eq,
    })),
  }
}

export async function adminApproveProduct(id) {
  return unwrap(await api.post(`/api/admin/equipments/${id}/approve`))
}

export async function adminRejectProduct(id) {
  return unwrap(await api.post(`/api/admin/equipments/${id}/reject`))
}

export async function adminToggleProductOnline(id, online) {
  // Backend only provides "off shelf" for admin; "online" should be approve.
  if (online) return adminApproveProduct(id)
  return unwrap(await api.post(`/api/admin/equipments/${id}/off_shelf`))
}

export async function adminDeleteProduct(id) {
  return unwrap(await api.delete(`/api/admin/equipments/${id}/delete`))
}

/** 首页精选展示（管理员） */
export async function adminListHomeMarquee() {
  return unwrap(await api.get('/api/admin/home-marquee'))
}

/** multipart：字段 title, subtitle?, track?, sort_order?, enabled?, image(文件) */
export async function adminCreateHomeMarquee(formData) {
  return unwrap(await api.post('/api/admin/home-marquee', formData))
}

/** JSON：title, image_url 必填；subtitle, track, sort_order, enabled 可选 */
export async function adminCreateHomeMarqueeJson(body) {
  return unwrap(await api.post('/api/admin/home-marquee', body))
}

export async function adminPatchHomeMarquee(id, body) {
  return unwrap(await api.patch(`/api/admin/home-marquee/${id}`, body))
}

/** 修改含新图片时用 FormData（可含 title, subtitle, track, sort_order, enabled, image） */
export async function adminPatchHomeMarqueeForm(id, formData) {
  return unwrap(await api.patch(`/api/admin/home-marquee/${id}`, formData))
}

export async function adminDeleteHomeMarquee(id) {
  return unwrap(await api.delete(`/api/admin/home-marquee/${id}`))
}

