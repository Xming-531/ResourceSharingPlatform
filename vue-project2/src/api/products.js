import { api, unwrap } from '@/api/client'

/**
 * 与 Django `_effective_listing_type` 一致：category 为「出租/出售」时决定交易类型，避免与 listing_type 字段不一致。
 */
export function effectiveListingType(eq) {
  const c = (eq.category || '').trim()
  if (c === '出售') return 'sale'
  if (c === '出租') return 'rent'
  return (eq.listing_type || '').trim() === 'sale' ? 'sale' : 'rent'
}

/** 后端：category=租售（出租/出售），title=商品类型（相机/镜头…）；兼容旧数据 category 存器材类型的情况 */
export function normalizeRentAndType(eq) {
  const c = (eq.category || '').trim()
  const isRentSell = c === '出租' || c === '出售'
  const lt = effectiveListingType(eq)
  const rentSell = lt === 'sale' ? '出售' : '出租'
  const type = isRentSell ? (eq.title || '').trim() || '其他' : c || (eq.title || '').trim() || '其他'
  return { rentSell, type }
}

export async function listPublicProducts(params) {
  const res = unwrap(await api.get('/api/equipments', { params }))
  const list = res?.data || []
  return {
    ...res,
    data: list.map((eq) => {
      const { rentSell, type } = normalizeRentAndType(eq)
      return {
        id: String(eq.equipment_id),
        title: `${eq.brand || ''}${eq.brand && eq.model ? ' ' : ''}${eq.model || ''}`.trim() || eq.title,
        rentSell,
        type,
        intro: eq.description,
        pricePerDay: Number(eq.price),
        deposit: Number(eq.deposit || 0),
        status: eq.status,
        image: eq.cover_img_url || '',
        isFavorited: Boolean(eq.is_favorited),
        raw: eq,
      }
    }),
  }
}

export async function createMyProduct(payload) {
  // Django: POST /api/equipments/create (creates 待审核)
  return unwrap(
    await api.post('/api/equipments/create', payload, {
      headers: payload instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : undefined,
    }),
  )
}

export async function listMyProducts() {
  const res = unwrap(await api.get('/api/my/equipments'))
  const list = res?.data || []
  return {
    ...res,
    data: list.map((eq) => {
      const { rentSell, type } = normalizeRentAndType(eq)
      return {
        id: String(eq.equipment_id),
        title:
          `${eq.brand || ''}${eq.brand && eq.model ? ' ' : ''}${eq.model || ''}`.trim() ||
          eq.title,
        pricePerDay: Number(eq.price),
        status: eq.status,
        rentSell,
        type,
        raw: eq,
      }
    }),
  }
}

export async function updateMyProduct(id, payload) {
  return unwrap(
    await api.patch(`/api/my/equipments/${id}`, payload, {
      headers: payload instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : undefined,
    }),
  )
}

export async function takeDownMyProduct(id) {
  return unwrap(await api.post(`/api/my/equipments/${id}/off_shelf`))
}

export async function deleteMyProduct(id) {
  return unwrap(await api.delete(`/api/my/equipments/${id}/delete`))
}

export async function onShelfMyProduct(id) {
  return unwrap(await api.post(`/api/my/equipments/${id}/on_shelf`))
}

export async function withdrawMyProduct(id) {
  return unwrap(await api.post(`/api/my/equipments/${id}/withdraw`))
}

