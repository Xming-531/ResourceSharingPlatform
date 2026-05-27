import { api, unwrap } from '@/api/client'

export async function fetchMyBillingMessages() {
  return unwrap(await api.get('/api/my/billing-messages'))
}

export async function deleteBillingMessage(messageId) {
  return unwrap(await api.delete(`/api/my/billing-messages/${messageId}/delete`))
}
