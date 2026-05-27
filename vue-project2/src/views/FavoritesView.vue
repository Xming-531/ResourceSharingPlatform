<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchMyFavorites, removeFavorite } from '@/api/favorites'
import { effectiveListingType, normalizeRentAndType } from '@/api/products'
import { useCart } from '@/composables/useCart'

const router = useRouter()
const loading = ref(false)
const items = ref([])
const err = ref('')
const toast = ref('')

const { addToCart } = useCart()

const detailOpen = ref(false)
const detailProduct = ref(null)
const detailDays = ref(1)

function showToast(msg) {
  toast.value = msg
  setTimeout(() => {
    toast.value = ''
  }, 2600)
}

/** ISO 时间 → 2026年04月09日14时30分（本地时区） */
function formatFavoritedAt(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  const y = d.getFullYear()
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${y}年${mo}月${day}日${h}时${mi}分`
}

function mapRow(eq) {
  const { rentSell, type } = normalizeRentAndType(eq)
  return {
    id: String(eq.equipment_id),
    title: `${eq.brand || ''}${eq.brand && eq.model ? ' ' : ''}${eq.model || ''}`.trim() || eq.title,
    rentSell,
    type,
    pricePerDay: Number(eq.price),
    deposit: Number(eq.deposit || 0),
    image: eq.cover_img_url || '',
    favoritedAt: formatFavoritedAt(eq.favorited_at),
    viewCount: Number(eq.view_count || 0),
    raw: eq,
  }
}

async function load() {
  loading.value = true
  err.value = ''
  try {
    const res = await fetchMyFavorites()
    if (!res?.ok) throw new Error(res?.message || '加载失败')
    const list = res?.data || []
    items.value = list.map(mapRow)
  } catch (e) {
    err.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function onRemove(row) {
  if (!confirm('确定取消收藏？')) return
  try {
    const id = Number(row.raw?.equipment_id)
    const res = await removeFavorite(id)
    if (!res?.ok) throw new Error(res?.message || '操作失败')
    items.value = items.value.filter((x) => x.id !== String(id))
  } catch (e) {
    alert(e?.message || '失败')
  }
}

function goHome() {
  router.push({ name: 'home' })
}

const detailIsSale = computed(() => {
  const p = detailProduct.value
  if (!p?.raw) return false
  return effectiveListingType(p.raw) === 'sale'
})

function openDetail(p) {
  detailProduct.value = p
  detailDays.value = 1
  detailOpen.value = true

  // 浏览量 +1（不阻塞弹窗打开）
  const eid = Number(p?.raw?.equipment_id)
  if (eid) {
    fetch(`/api/equipments/${eid}/view`, { method: 'POST' })
      .then((r) => r.json())
      .then((j) => {
        if (!j?.ok) return
        const next = Number(j?.data?.view_count)
        if (!Number.isFinite(next)) return
        // 更新详情与列表项
        if (detailProduct.value?.raw?.equipment_id === eid) {
          detailProduct.value.raw.view_count = next
          detailProduct.value.viewCount = next
        }
        const hit = items.value.find((x) => Number(x?.raw?.equipment_id) === eid)
        if (hit) {
          hit.raw.view_count = next
          hit.viewCount = next
        }
      })
      .catch(() => null)
  }
}

function closeDetail() {
  detailOpen.value = false
  detailProduct.value = null
}

function addFromDetail() {
  const p = detailProduct.value
  if (!p?.raw) return
  const raw = p.raw
  const lt = effectiveListingType(raw)
  const days = lt === 'sale' ? 1 : Math.max(1, Number(detailDays.value) || 1)
  if (lt !== 'sale' && days < 1) {
    showToast('租用天数至少为 1')
    return
  }
  addToCart({
    equipment_id: raw.equipment_id,
    listing_type: lt,
    rental_days: days,
    product: p,
  })
  showToast('已加入购物车')
  closeDetail()
}
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">收藏管理</div>
      <div class="sub">已收藏的商品列表；取消收藏后将从本页移除。</div>
      <button class="btn" type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button>
    </div>

    <p v-if="err" class="err">{{ err }}</p>

    <div v-if="!loading && !items.length && !err" class="empty">暂无收藏，去首页点亮星标即可添加。</div>

    <div class="grid">
      <article v-for="r in items" :key="r.id" class="card">
        <div class="card__img">
          <img v-if="r.image" :src="r.image" :alt="r.title" loading="lazy" />
          <div v-else class="placeholder">暂无封面</div>
        </div>
        <div class="card__body">
          <div class="card__badges">
            <span class="badge" :class="r.rentSell === '出售' ? 'badge--sale' : 'badge--rent'">{{ r.rentSell }}</span>
            <span class="badge badge--muted">{{ r.type }}</span>
          </div>
          <div class="card__name" :title="r.title">{{ r.title }}</div>
          <div class="row muted">浏览量：{{ r.viewCount ?? (r.raw?.view_count || 0) }}</div>
          <div class="row muted">收藏时间：{{ r.favoritedAt || '—' }}</div>
          <div class="card__foot">
            <div class="price">
              <template v-if="r.rentSell !== '出售'">
                ¥{{ r.pricePerDay }}<span class="unit">/天</span>
                <span class="dep">押¥{{ r.deposit }}</span>
              </template>
              <template v-else>¥{{ r.pricePerDay }}</template>
            </div>
            <div class="acts">
              <button class="btn" type="button" @click="openDetail(r)">查看详情</button>
              <button class="btn danger" type="button" @click="onRemove(r)">取消收藏</button>
            </div>
          </div>
        </div>
      </article>
    </div>

    <div class="footer-act">
      <button class="btn primary" type="button" @click="goHome">去首页逛逛</button>
    </div>
  </section>

  <!-- 详情弹窗（与首页一致：浏览量、租期、加入购物车） -->
  <Teleport to="body">
    <div v-if="detailOpen" class="modal-backdrop" @click.self="closeDetail">
      <div class="modal panel" role="dialog" aria-modal="true">
        <div class="modal__title">商品详情</div>
        <template v-if="detailProduct?.raw">
          <div class="detail-row"><span class="k">名称</span>{{ detailProduct.raw.title || detailProduct.title }}</div>
          <div class="detail-row"><span class="k">分类</span>{{ detailProduct.raw.category }}</div>
          <div class="detail-row"><span class="k">浏览量</span>{{ detailProduct.raw.view_count || 0 }}</div>
          <div class="detail-row"><span class="k">品牌/型号</span>{{ detailProduct.raw.brand }} {{ detailProduct.raw.model }}</div>
          <div class="detail-row detail-row--block">
            <span class="k">描述</span>
            <p class="desc">{{ detailProduct.raw.description }}</p>
          </div>
          <div class="detail-row detail-row--price">
            <span class="k">价格</span>
            <span class="detail-price-value">
              ¥{{ detailProduct.raw.price }}<template v-if="!detailIsSale">（日租金）</template>
            </span>
          </div>
          <div class="detail-row"><span class="k">押金</span>¥{{ detailProduct.raw.deposit }}</div>
          <div class="detail-row"><span class="k">位置</span>{{ detailProduct.raw.location }}</div>
          <div v-if="!detailIsSale" class="detail-row detail-row--days">
            <span class="k">租用天数</span>
            <input v-model.number="detailDays" class="days-inp" type="number" min="1" step="1" />
          </div>
          <p v-else class="sale-hint">出售商品：数量为 1 件</p>
        </template>
        <div class="modal__actions">
          <button class="btn primary" type="button" @click="addFromDetail">加入购物车</button>
          <button class="btn" type="button" @click="closeDetail">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>

  <div v-if="toast" class="toast">{{ toast }}</div>
</template>

<style scoped>
.page {
  padding: 4px 4px 24px;
}
.head {
  padding: 6px 6px 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
}
.title {
  font-size: 18px;
  font-weight: 900;
}
.sub {
  font-size: 13px;
  opacity: 0.7;
  flex: 1;
  min-width: 200px;
}
.err {
  color: #b91c1c;
  font-size: 14px;
  margin-bottom: 12px;
}
.empty {
  font-size: 14px;
  opacity: 0.7;
  padding: 12px 0;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.card {
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  display: grid;
  grid-template-rows: 160px 1fr;
}
@media (prefers-color-scheme: dark) {
  .card {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.card__img {
  background: rgba(2, 6, 23, 0.08);
}
.card__img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.placeholder {
  height: 100%;
  display: grid;
  place-items: center;
  font-size: 13px;
  opacity: 0.65;
}
.card__body {
  padding: 12px;
  display: grid;
  gap: 6px;
}
.card__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.badge {
  font-size: 11px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 999px;
}
.badge--rent {
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.35);
}
.badge--sale {
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.35);
}
.badge--muted {
  opacity: 0.85;
  border: 1px solid rgba(15, 23, 42, 0.12);
}
.card__name {
  font-weight: 900;
  line-height: 1.3;
}
.row {
  font-size: 12px;
}
.muted {
  opacity: 0.72;
}
.card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 6px;
}
.price {
  font-weight: 900;
  font-size: 14px;
}
.unit {
  font-size: 12px;
  opacity: 0.75;
}
.dep {
  display: block;
  font-size: 11px;
  font-weight: 700;
  opacity: 0.65;
}
.acts {
  display: flex;
  gap: 8px;
}
.btn {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.4);
  color: inherit;
  border-radius: 12px;
  padding: 8px 12px;
  cursor: pointer;
  font-weight: 800;
  font-size: 13px;
}
.btn.primary {
  border-color: rgba(99, 102, 241, 0.28);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.95), rgba(59, 130, 246, 0.95));
  color: white;
}
.btn.danger {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.1);
}
.footer-act {
  margin-top: 20px;
}

/* modal (copied minimal from HomeView style) */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.modal.panel {
  width: 100%;
  max-width: 440px;
  max-height: 90vh;
  overflow: auto;
  border-radius: 16px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(15, 23, 42, 0.1);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
}
@media (prefers-color-scheme: dark) {
  .modal.panel {
    background: rgba(15, 23, 42, 0.96);
    border-color: rgba(148, 163, 184, 0.2);
  }
}
.modal__title {
  font-size: 17px;
  font-weight: 900;
  margin-bottom: 12px;
}
.modal__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}
.detail-row {
  font-size: 14px;
  margin-bottom: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.detail-row--block {
  flex-direction: column;
}
.detail-row--price {
  flex-wrap: nowrap;
  align-items: baseline;
}
.detail-price-value {
  white-space: nowrap;
}
.k {
  font-weight: 800;
  opacity: 0.65;
  min-width: 4.5rem;
}
.desc {
  margin: 4px 0 0;
  opacity: 0.85;
  line-height: 1.5;
}
.days-inp {
  width: 5rem;
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.15);
}
.sale-hint {
  font-size: 13px;
  opacity: 0.75;
  margin: 8px 0 0;
}
.toast {
  position: fixed;
  top: 88px;
  right: 16px;
  z-index: 2100;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.92);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  max-width: 300px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}
</style>
