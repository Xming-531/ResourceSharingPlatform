import { api, unwrap } from '@/api/client'

export async function checkoutOrder(body) {
  return unwrap(await api.post('/api/orders/checkout', body))
}

export async function fetchMyOrders() {
  return unwrap(await api.get('/api/my/orders'))
}

export async function fetchSalesOrders() {
  return unwrap(await api.get('/api/my/sales-orders'))
}

export async function fetchAdminOrders(params) {
  return unwrap(await api.get('/api/admin/orders', { params }))
}

export async function fetchAdminOrderDetail(orderId) {
  return unwrap(await api.get(`/api/admin/orders/${orderId}`))
}

export async function fetchOrderDetail(orderId) {
  return unwrap(await api.get(`/api/orders/${orderId}`))
}

export async function confirmHandoverOwner(orderId) {
  return unwrap(await api.post(`/api/orders/${orderId}/confirm-handover-owner`, {}))
}

export async function confirmHandoverBuyer(orderId) {
  return unwrap(await api.post(`/api/orders/${orderId}/confirm-handover-buyer`, {}))
}

export async function confirmReturnOwner(orderId) {
  return unwrap(await api.post(`/api/orders/${orderId}/confirm-return-owner`, {}))
}

export async function confirmReturnBuyer(orderId) {
  return unwrap(await api.post(`/api/orders/${orderId}/confirm-return-buyer`, {}))
}

/** 买家确认提前归还（需卖家也确认后进入待归还） */
export async function requestEarlyReturn(orderId) {
  return unwrap(await api.post(`/api/orders/${orderId}/early-return`, {}))
}

/** 卖家确认提前归还 */
export async function requestEarlyReturnOwner(orderId) {
  return unwrap(await api.post(`/api/orders/${orderId}/early-return-owner`, {}))
}

/** 卖家驳回提前归还申请，买家可再次申请 */
export async function rejectEarlyReturnOwner(orderId) {
  return unwrap(await api.post(`/api/orders/${orderId}/early-return-owner-reject`, {}))
}

/** 租借方按时归还：租期届满前 N 小时内发起，待出租方确认后直接完成 */
export async function requestNormalReturn(orderId) {
  return unwrap(await api.post(`/api/orders/${orderId}/request-normal-return`, {}))
}

/** 出租方确认按时归还，订单直接完成并结算 */
export async function confirmNormalReturnOwner(orderId) {
  return unwrap(await api.post(`/api/orders/${orderId}/confirm-normal-return-owner`, {}))
}

/** 租借方：已超期时进入待归还，双方再确认后结算（含超期扣费） */
export async function requestOverdueReturn(orderId) {
  return unwrap(await api.post(`/api/orders/${orderId}/request-overdue-return`, {}))
}

/** 买家或卖家删除「已完成」订单 */
export async function deleteOrder(orderId) {
  return unwrap(await api.delete(`/api/orders/${orderId}/delete`))
}

/** 管理员删除「已完成」订单 */
export async function deleteAdminOrder(orderId) {
  return unwrap(await api.delete(`/api/admin/orders/${orderId}/delete`))
}
