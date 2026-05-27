import { api, unwrap } from '@/api/client'

export async function fetchWorksPublic() {
  return unwrap(await api.get('/api/works'))
}

export async function fetchMyWorks() {
  return unwrap(await api.get('/api/my/works'))
}

export async function fetchMyWorkComments() {
  return unwrap(await api.get('/api/my/work-comments'))
}

export async function fetchMyWork(workId) {
  return unwrap(await api.get(`/api/my/works/${workId}`))
}

export async function updateMyWork(workId, payload) {
  return unwrap(await api.patch(`/api/my/works/${workId}`, payload))
}

export async function reapplyMyWork(workId) {
  return unwrap(await api.post(`/api/my/works/${workId}/reapply`, {}))
}

export async function withdrawMyWork(workId) {
  return unwrap(await api.post(`/api/my/works/${workId}/withdraw`, {}))
}

export async function offShelfMyWork(workId) {
  return unwrap(await api.post(`/api/my/works/${workId}/off_shelf`, {}))
}

export async function deleteMyWork(workId) {
  return unwrap(await api.delete(`/api/my/works/${workId}/delete`))
}

export async function createWork(formData) {
  return unwrap(
    await api.post('/api/my/works/create', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  )
}

export async function adminFetchWorks(params) {
  return unwrap(await api.get('/api/admin/works', { params }))
}

export async function adminApproveWork(workId) {
  return unwrap(await api.post(`/api/admin/works/${workId}/approve`, {}))
}

export async function adminRejectWork(workId) {
  return unwrap(await api.post(`/api/admin/works/${workId}/reject`, {}))
}

export async function adminOffShelfWork(workId) {
  return unwrap(await api.post(`/api/admin/works/${workId}/off_shelf`, {}))
}

export async function adminOnShelfWork(workId) {
  return unwrap(await api.post(`/api/admin/works/${workId}/on_shelf`, {}))
}

export async function adminDeleteWork(workId) {
  // 使用 POST：与 approve/reject/off_shelf 一致，且避免部分代理/宿主对 DELETE 的异常处理
  return unwrap(await api.post(`/api/admin/works/${workId}/delete`, {}))
}

export async function fetchWorkComments(workId) {
  return unwrap(await api.get(`/api/works/${workId}/comments`))
}

export async function postWorkComment(workId, content) {
  return unwrap(await api.post(`/api/works/${workId}/comments`, { content }))
}

export async function deleteWorkComment(workId, commentId) {
  return unwrap(await api.delete(`/api/works/${workId}/comments/${commentId}`))
}

export async function adminFetchWorkComments(params) {
  return unwrap(await api.get('/api/admin/work-comments', { params }))
}

export async function adminApproveWorkComment(commentId) {
  return unwrap(await api.post(`/api/admin/work-comments/${commentId}/approve`, {}))
}

export async function adminRejectWorkComment(commentId) {
  return unwrap(await api.post(`/api/admin/work-comments/${commentId}/reject`, {}))
}

export async function adminDeleteWorkComment(commentId) {
  return unwrap(await api.delete(`/api/admin/work-comments/${commentId}`))
}

