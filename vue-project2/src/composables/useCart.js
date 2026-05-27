import { computed, onMounted, ref, watch } from 'vue'
import { effectiveListingType } from '@/api/products'

const CART_KEY = 'camera_platform_cart_v1'

function loadRaw() {
  try {
    const raw = localStorage.getItem(CART_KEY)
    if (!raw) return []
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

export function lineTotalFromProduct(eq, rentalDays) {
  if (!eq) return 0
  const price = Number(eq.price)
  const dep = Number(eq.deposit || 0)
  const lt = effectiveListingType(eq)
  if (lt === 'sale') return price
  const d = Math.max(1, Number(rentalDays) || 1)
  return price * d + dep
}

export function useCart() {
  const lines = ref([])

  onMounted(() => {
    lines.value = loadRaw()
  })

  watch(
    lines,
    (v) => {
      localStorage.setItem(CART_KEY, JSON.stringify(v))
    },
    { deep: true },
  )

  const count = computed(() => lines.value.length)

  const total = computed(() => {
    return lines.value.reduce((sum, line) => {
      const eq = line._product
      if (!eq) return sum
      return sum + lineTotalFromProduct(eq, line.rental_days)
    }, 0)
  })

  function attachProducts(products) {
    const map = new Map(products.map((p) => [String(p.id), p.raw]))
    lines.value = lines.value.map((line) => {
      const raw = map.get(String(line.equipment_id)) || line._product
      if (!raw) return { ...line }
      const lt = effectiveListingType(raw)
      return {
        ...line,
        listing_type: lt,
        rental_days: lt === 'sale' ? 1 : Math.max(1, Number(line.rental_days) || 1),
        _product: raw,
      }
    })
  }

  function addToCart({ equipment_id, listing_type, rental_days, product }) {
    const id = String(equipment_id)
    const days = listing_type === 'sale' ? 1 : Math.max(1, Number(rental_days) || 1)
    const idx = lines.value.findIndex((l) => String(l.equipment_id) === id)
    if (idx >= 0) {
      if (listing_type === 'sale') {
        lines.value[idx] = {
          ...lines.value[idx],
          rental_days: 1,
          listing_type,
          _product: product?.raw ? product.raw : lines.value[idx]._product,
        }
      } else {
        lines.value[idx] = {
          ...lines.value[idx],
          rental_days: lines.value[idx].rental_days + days,
          listing_type,
          _product: product?.raw ? product.raw : lines.value[idx]._product,
        }
      }
    } else {
      lines.value.push({
        equipment_id: Number(equipment_id),
        rental_days: days,
        listing_type,
        _product: product?.raw || null,
      })
    }
  }

  function setLineDays(equipment_id, nextDays) {
    const id = String(equipment_id)
    const idx = lines.value.findIndex((l) => String(l.equipment_id) === id)
    if (idx < 0) return
    const line = lines.value[idx]
    if (line.listing_type === 'sale') {
      if (nextDays <= 0) lines.value.splice(idx, 1)
      else lines.value[idx] = { ...line, rental_days: 1 }
      return
    }
    if (nextDays <= 0) lines.value.splice(idx, 1)
    else lines.value[idx] = { ...line, rental_days: nextDays }
  }

  function clearCart() {
    lines.value = []
  }

  function payloadForCheckout() {
    return lines.value.map((l) => ({
      equipment_id: l.equipment_id,
      rental_days: l.rental_days,
    }))
  }

  return {
    lines,
    count,
    total,
    addToCart,
    setLineDays,
    clearCart,
    payloadForCheckout,
    attachProducts,
  }
}

