import { api, unwrap } from '@/api/client'

export async function fetchMyFavorites() {
  return unwrap(await api.get('/api/my/favorites'))
}

export async function addFavorite(equipmentId) {
  return unwrap(await api.post('/api/my/favorites/add', { equipment_id: equipmentId }))
}

export async function removeFavorite(equipmentId) {
  return unwrap(await api.delete(`/api/my/favorites/${equipmentId}`))
}

