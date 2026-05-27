<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { effectiveListingType, listPublicProducts } from '@/api/products'
import { addFavorite, removeFavorite } from '@/api/favorites'
import { checkoutOrder } from '@/api/orders'
import { goLogin } from '@/utils/authNavigate'
import { getSession, isLoggedIn } from '@/utils/session'
import { lineTotalFromProduct, useCart } from '@/composables/useCart'
import ImageLightbox from '@/components/ImageLightbox.vue'
import { fetchHomeMarquee } from '@/api/marquee'

const router = useRouter()
const route = useRoute()

const categories = [
  { id: 'all', name: '全部' },
  { id: '相机', name: '相机' },
  { id: '镜头', name: '镜头' },
  { id: '闪光灯', name: '闪光灯' },
  { id: '稳定器', name: '稳定器' },
  { id: '三脚架', name: '三脚架' },
  { id: '其他', name: '其他' },
]

const activeCategoryId = ref('all')
const activeRentSell = ref('all')
const searchQuery = ref('')

const resources = ref([])
const loading = ref(false)
let searchDebounce = null

const {
  lines: cartLines,
  count: cartCount,
  total: cartTotal,
  addToCart,
  setLineDays,
  clearCart,
  payloadForCheckout,
  attachProducts,
} = useCart()

const detailOpen = ref(false)
const detailProduct = ref(null)
const detailDays = ref(1)

const cartModalOpen = ref(false)
const checkoutOpen = ref(false)
const checkoutAddress = ref('')
const checkoutPhone = ref('')
const checkoutBusy = ref(false)
const identityPromptOpen = ref(false)
const toast = ref('')

const identityVerified = computed(() => {
  void sessionTick.value
  const u = getSession()?.user
  return !!(u && u.identity_verified)
})

const imageLightboxOpen = ref(false)
const imageLightboxSrc = ref('')
const imageLightboxAlt = ref('')

const marqueeTrack1 = ref([])
const marqueeTrack2 = ref([])
const marqueeHover = ref('')

const marqueeHasAny = computed(
  () => marqueeTrack1.value.length > 0 || marqueeTrack2.value.length > 0,
)

function resolveMarqueeImageUrl(u) {
  if (!u || typeof u !== 'string') return ''
  const t = u.trim()
  if (!t) return ''
  if (/^https?:\/\//i.test(t)) return t
  const base = import.meta.env.VITE_API_BASE_URL || ''
  return t.startsWith('/') ? `${base}${t}` : `${base}/${t}`
}

async function loadMarquee() {
  try {
    const res = await fetchHomeMarquee()
    if (!res?.ok) return
    const d = res.data || {}
    marqueeTrack1.value = Array.isArray(d.track1) ? d.track1 : []
    marqueeTrack2.value = Array.isArray(d.track2) ? d.track2 : []
  } catch {
    marqueeTrack1.value = []
    marqueeTrack2.value = []
  }
}

function showToast(msg) {
  toast.value = msg
  setTimeout(() => {
    toast.value = ''
  }, 2800)
}

async function fetchResources() {
  loading.value = true
  try {
    const q = searchQuery.value.trim()
    const params = q ? { q } : {}
    const res = await listPublicProducts(params)
    resources.value = res?.data || []
    attachProducts(resources.value)
  } catch (e) {
    showToast(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const sessionTick = ref(0)
function bumpSessionTick() {
  sessionTick.value += 1
}
onMounted(() => {
  fetchResources()
  loadMarquee()
  window.addEventListener('session-changed', bumpSessionTick)
})
onUnmounted(() => {
  window.removeEventListener('session-changed', bumpSessionTick)
})

watch(searchQuery, () => {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    fetchResources()
  }, 350)
})

watch(resources, (list) => attachProducts(list), { deep: true })

const filteredResources = computed(() => {
  let list = resources.value
  if (activeRentSell.value !== 'all') {
    list = list.filter((r) => r.rentSell === activeRentSell.value)
  }
  if (activeCategoryId.value !== 'all') {
    list = list.filter((r) => r.type === activeCategoryId.value)
  }
  return list
})

/** 当前选中的器材分类在全部公开展示中是否一条都没有（不受出租/出售筛选影响） */
const hasAnyInSelectedEquipmentCategory = computed(() => {
  if (activeCategoryId.value === 'all') return true
  return resources.value.some((r) => r.type === activeCategoryId.value)
})

/**
 * 具体器材分类下完全没有该类型上架商品时，展示引导发布文案；
 * 若有该类型但被出租/出售或搜索筛空，则用通用空状态文案。
 */
const showCategoryNoListingsHint = computed(() => {
  if (loading.value) return false
  if (filteredResources.value.length > 0) return false
  if (activeCategoryId.value === 'all') return false
  if (searchQuery.value.trim()) return false
  return !hasAnyInSelectedEquipmentCategory.value
})

async function toggleFavorite(r, ev) {
  if (ev) ev.stopPropagation()
  if (!isLoggedIn()) {
    showToast('请先登录后收藏')
    goLogin(router, route.fullPath)
    return
  }
  const id = Number(r.raw?.equipment_id)
  if (!id) return
  try {
    if (r.isFavorited) {
      const res = await removeFavorite(id)
      if (!res?.ok) throw new Error(res?.message || '取消收藏失败')
      r.isFavorited = false
      if (r.raw) r.raw.is_favorited = false
      showToast('已取消收藏')
    } else {
      const res = await addFavorite(id)
      if (!res?.ok) throw new Error(res?.message || '收藏失败')
      r.isFavorited = true
      if (r.raw) r.raw.is_favorited = true
      showToast('已加入收藏')
    }
  } catch (e) {
    showToast(e?.message || '操作失败')
  }
}

/** 详情弹窗：出售不写「日租金」 */
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

        // 更新详情弹窗
        if (detailProduct.value?.raw?.equipment_id === eid) {
          detailProduct.value.raw.view_count = next
          detailProduct.value.viewCount = next
        }
        // 更新列表项
        const hit = resources.value.find((x) => Number(x?.raw?.equipment_id) === eid)
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

function confirmAddToCart() {
  if (!isLoggedIn()) {
    showToast('请先登录后加入购物车')
    goLogin(router, route.fullPath)
    return
  }
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

function lineSubtotal(line) {
  return lineTotalFromProduct(line._product, line.rental_days)
}

function closeIdentityPrompt() {
  identityPromptOpen.value = false
}

function goProfileForVerify() {
  closeIdentityPrompt()
  router.push({ name: 'profile' })
}

function openCheckout() {
  if (!isLoggedIn()) {
    showToast('请先登录后下单')
    goLogin(router, route.fullPath)
    return
  }
  if (!identityVerified.value) {
    identityPromptOpen.value = true
    return
  }
  const s = getSession()
  checkoutPhone.value = s?.user?.phone || ''
  checkoutAddress.value = ''
  checkoutOpen.value = true
}

async function submitCheckout() {
  if (!isLoggedIn()) {
    goLogin(router, route.fullPath)
    return
  }
  if (!identityVerified.value) {
    checkoutOpen.value = false
    identityPromptOpen.value = true
    return
  }
  const addr = checkoutAddress.value.trim()
  const phone = checkoutPhone.value.trim()
  if (!addr || !phone) {
    showToast('请填写收货地址与联系电话')
    return
  }
  if (!cartLines.value.length) {
    showToast('购物车为空')
    return
  }
  checkoutBusy.value = true
  try {
    const res = await checkoutOrder({
      shipping_address: addr,
      contact_phone: phone,
      items: payloadForCheckout(),
    })
    if (!res?.ok) {
      showToast(res?.message || '下单失败')
      return
    }
    const ids = res.data?.order_ids ?? []
    clearCart()
    checkoutOpen.value = false
    cartModalOpen.value = false
    if (ids.length === 1) {
      showToast(`下单成功，订单号 ${ids[0]}`)
    } else if (ids.length <= 4) {
      showToast(`下单成功，已生成 ${ids.length} 笔订单：#${ids.join('、#')}`)
    } else {
      showToast(`下单成功，已生成 ${ids.length} 笔订单，请至订单管理查看`)
    }
    router.push({ name: 'orders' })
  } catch (e) {
    showToast(e?.message || '网络错误')
  } finally {
    checkoutBusy.value = false
  }
}

function cartLineDisplayTitle(line) {
  const eq = line._product
  if (!eq) return `#${line.equipment_id}`
  const t = `${eq.brand || ''}${eq.brand && eq.model ? ' ' : ''}${eq.model || ''}`.trim()
  return t || eq.title || `#${line.equipment_id}`
}

function openProductImageLightbox(r) {
  if (!r?.image) return
  imageLightboxSrc.value = r.image
  imageLightboxAlt.value = r.title || '商品封面'
  imageLightboxOpen.value = true
}
</script>

<template>
  <div class="page">
    <section v-if="marqueeHasAny" class="home-marquee" aria-label="精选展示">
      <div class="home-marquee__head">
        <span class="home-marquee__label">精选展示</span>
        <span class="home-marquee__hint">将鼠标移入可暂停滚动</span>
      </div>

      <div
        v-if="marqueeTrack1.length"
        class="marquee-row"
        @mouseenter="marqueeHover = 't1'"
        @mouseleave="marqueeHover = ''"
      >
        <div
          class="marquee-track marquee-track--fast"
          :class="{ 'is-paused': marqueeHover === 't1' }"
        >
          <div class="marquee-group">
            <article v-for="it in marqueeTrack1" :key="'t1a-' + it.id" class="marquee-card">
              <img
                class="marquee-card__img"
                :src="resolveMarqueeImageUrl(it.image_url)"
                :alt="it.title"
                width="200"
                height="112"
                loading="lazy"
              />
              <div class="marquee-card__overlay">
                <strong class="marquee-card__title">{{ it.title }}</strong>
                <span v-if="it.subtitle" class="marquee-card__sub">{{ it.subtitle }}</span>
              </div>
            </article>
          </div>
          <div class="marquee-group" aria-hidden="true">
            <article v-for="it in marqueeTrack1" :key="'t1b-' + it.id" class="marquee-card">
              <img
                class="marquee-card__img"
                :src="resolveMarqueeImageUrl(it.image_url)"
                alt=""
                width="200"
                height="112"
                loading="lazy"
              />
              <div class="marquee-card__overlay">
                <strong class="marquee-card__title">{{ it.title }}</strong>
                <span v-if="it.subtitle" class="marquee-card__sub">{{ it.subtitle }}</span>
              </div>
            </article>
          </div>
        </div>
      </div>

      <div
        v-if="marqueeTrack2.length"
        class="marquee-row"
        @mouseenter="marqueeHover = 't2'"
        @mouseleave="marqueeHover = ''"
      >
        <div
          class="marquee-track marquee-track--slow"
          :class="{ 'is-paused': marqueeHover === 't2' }"
        >
          <div class="marquee-group">
            <article v-for="it in marqueeTrack2" :key="'t2a-' + it.id" class="marquee-card">
              <img
                class="marquee-card__img"
                :src="resolveMarqueeImageUrl(it.image_url)"
                :alt="it.title"
                width="200"
                height="112"
                loading="lazy"
              />
              <div class="marquee-card__overlay">
                <strong class="marquee-card__title">{{ it.title }}</strong>
                <span v-if="it.subtitle" class="marquee-card__sub">{{ it.subtitle }}</span>
              </div>
            </article>
          </div>
          <div class="marquee-group" aria-hidden="true">
            <article v-for="it in marqueeTrack2" :key="'t2b-' + it.id" class="marquee-card">
              <img
                class="marquee-card__img"
                :src="resolveMarqueeImageUrl(it.image_url)"
                alt=""
                width="200"
                height="112"
                loading="lazy"
              />
              <div class="marquee-card__overlay">
                <strong class="marquee-card__title">{{ it.title }}</strong>
                <span v-if="it.subtitle" class="marquee-card__sub">{{ it.subtitle }}</span>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>

    <div class="content">
      <aside class="sidebar">
        <div class="sidebar__title">分类</div>

        <div class="sidebar__subTitle">交易类型</div>
        <nav class="cats" aria-label="出租出售分类">
          <button class="cat" :class="{ active: activeRentSell === 'all' }" type="button" @click="activeRentSell = 'all'">
            全部
          </button>
          <button class="cat" :class="{ active: activeRentSell === '出租' }" type="button" @click="activeRentSell = '出租'">
            出租
          </button>
          <button class="cat" :class="{ active: activeRentSell === '出售' }" type="button" @click="activeRentSell = '出售'">
            出售
          </button>
        </nav>

        <div class="sidebar__subTitle" style="margin-top: 12px;">器材分类</div>
        <nav class="cats" aria-label="资源分类">
          <button
            v-for="c in categories"
            :key="c.id"
            class="cat"
            :class="{ active: c.id === activeCategoryId }"
            type="button"
            @click="activeCategoryId = c.id"
          >
            {{ c.name }}
          </button>
        </nav>
      </aside>

      <main class="main">
        <div class="search-bar">
          <label class="search-bar__label" for="home-product-search">搜索</label>
          <input
            id="home-product-search"
            v-model.trim="searchQuery"
            class="search-bar__input"
            type="search"
            placeholder="品牌或型号模糊搜索，如 Sony、24-70"
            autocomplete="off"
          />
        </div>
        <div class="main__head">
          <div class="main__title">
            {{ (activeRentSell === 'all' ? '全部' : activeRentSell) + ' · ' + (categories.find((c) => c.id === activeCategoryId)?.name || '全部') }}
          </div>
          <div class="main__count">
            <span v-if="loading">加载中...</span>
            <span v-else>共 {{ filteredResources.length }} 条资源</span>
          </div>
        </div>

        <div v-if="!loading && filteredResources.length === 0" class="empty-hint" role="status">
          <p v-if="showCategoryNoListingsHint" class="empty-hint__text">
            尚未有用户上架该类型的商品，快来发布吧！
          </p>
          <template v-else>
            <p class="empty-hint__text">当前条件下暂无上架商品。</p>
            <p class="empty-hint__sub">换个分类或搜索试试，或前往个人资源发布商品。</p>
          </template>
        </div>

        <div v-else class="grid">
          <article v-for="r in filteredResources" :key="r.id" class="card">
            <div class="card__img">
              <img
                v-if="r.image"
                class="card__img-el"
                :src="r.image"
                alt="商品封面，点击放大"
                loading="lazy"
                role="button"
                tabindex="0"
                @click="openProductImageLightbox(r)"
                @keydown.enter.prevent="openProductImageLightbox(r)"
                @keydown.space.prevent="openProductImageLightbox(r)"
              />
              <div v-else class="placeholder">暂无封面</div>
            </div>
            <div class="card__body">
              <div class="card__badges">
                <span class="badge" :class="r.rentSell === '出售' ? 'badge--sale' : 'badge--rent'">{{ r.rentSell }}</span>
              </div>
              <div class="card__name" :title="r.title">{{ r.title }}</div>
              <div class="card__meta">浏览量：{{ r.viewCount ?? (r.raw?.view_count || 0) }}</div>
              <div class="card__foot">
                <div class="price">
                  <template v-if="r.rentSell !== '出售'">
                    <span class="price__rent-line">¥{{ r.pricePerDay }}<span class="unit">/天</span></span>
                    <span class="dep">押¥{{ r.deposit }}</span>
                  </template>
                  <template v-else>
                    <span class="price__rent-line">¥{{ r.pricePerDay }}</span>
                  </template>
                </div>
                <div class="card__btns">
                  <button
                    type="button"
                    class="star-btn"
                    :class="{ 'star-btn--on': r.isFavorited }"
                    :title="r.isFavorited ? '取消收藏' : '加入收藏'"
                    aria-label="收藏"
                    @click="toggleFavorite(r, $event)"
                  >
                    ★
                  </button>
                  <button class="btn primary" type="button" @click="openDetail(r)">查看详情</button>
                </div>
              </div>
            </div>
          </article>
        </div>
      </main>
    </div>

    <ImageLightbox
      v-model:open="imageLightboxOpen"
      :src="imageLightboxSrc"
      :alt="imageLightboxAlt"
    />

    <!-- 商品详情 -->
    <Teleport to="body">
      <div v-if="detailOpen" class="modal-backdrop" @click.self="closeDetail">
        <div class="modal panel" role="dialog" aria-modal="true">
          <div class="modal__title">商品详情</div>
          <template v-if="detailProduct?.raw">
            <div class="detail-row">
              <span class="k">名称</span>{{ detailProduct.raw.title || detailProduct.title }}
            </div>
            <div class="detail-row"><span class="k">分类</span>{{ detailProduct.raw.category }}</div>
            <div class="detail-row">
              <span class="k">品牌/型号</span>{{ detailProduct.raw.brand }} {{ detailProduct.raw.model }}
            </div>
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
            <button class="btn primary" type="button" @click="confirmAddToCart">加入购物车</button>
            <button class="btn" type="button" @click="closeDetail">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 购物车弹窗 -->
    <Teleport to="body">
      <div v-if="cartModalOpen" class="modal-backdrop" @click.self="cartModalOpen = false">
        <div class="modal panel panel--wide" role="dialog" aria-modal="true">
          <div class="modal__title">购物车</div>
          <div v-if="!cartLines.length" class="empty-cart">购物车为空</div>
          <div v-else class="cart-lines">
            <div v-for="line in cartLines" :key="line.equipment_id" class="cart-line">
              <div class="cart-line__main">
                <div class="cart-line__title">
                  {{ cartLineDisplayTitle(line) }}
                  <span class="badge" :class="line.listing_type === 'sale' ? 'badge--sale' : 'badge--rent'">
                    {{ line.listing_type === 'sale' ? '出售' : '出租' }}
                  </span>
                </div>
                <div class="cart-line__sub">小计 ¥{{ lineSubtotal(line).toFixed(2) }}</div>
                <div class="cart-line__ctrl">
                  <template v-if="line.listing_type === 'sale'">
                    <button type="button" class="btn btn--sm" @click="setLineDays(line.equipment_id, 0)">移除</button>
                  </template>
                  <template v-else>
                    <button type="button" class="btn btn--sm" @click="setLineDays(line.equipment_id, line.rental_days - 1)">−</button>
                    <span class="days-label">{{ line.rental_days }} 天</span>
                    <button type="button" class="btn btn--sm" @click="setLineDays(line.equipment_id, line.rental_days + 1)">+</button>
                  </template>
                </div>
              </div>
            </div>
          </div>
          <div class="modal__footer">
            <span>合计 <strong class="money">¥{{ cartTotal.toFixed(2) }}</strong></span>
            <button class="btn" type="button" @click="cartModalOpen = false">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 未实名：提示（不强制跳转） -->
    <Teleport to="body">
      <div v-if="identityPromptOpen" class="modal-backdrop" @click.self="closeIdentityPrompt">
        <div class="modal panel identity-prompt" role="dialog" aria-modal="true">
          <div class="modal__title">需要实名认证</div>
          <p class="identity-prompt__text">
            为保障交易安全，下单前需完成实名认证（当前为模拟流程：在「个人信息」中点击「实名认证」即可）。
          </p>
          <p class="identity-prompt__sub">完成实名后返回此处即可正常结算，无需重新登录。</p>
          <div class="modal__actions identity-prompt__actions">
            <button class="btn" type="button" @click="closeIdentityPrompt">稍后再说</button>
            <button class="btn primary" type="button" @click="goProfileForVerify">去实名认证</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 结算 -->
    <Teleport to="body">
      <div v-if="checkoutOpen" class="modal-backdrop" @click.self="checkoutOpen = false">
        <div class="modal panel" role="dialog" aria-modal="true">
          <div class="modal__title">结算下单</div>
          <p class="hint">填写收货地址与联系电话。购物车中<strong>每件商品将各生成一笔独立订单</strong>，可同时包含出租、出售及不同卖家的商品。</p>
          <p class="hint hint--muted">下单需已完成实名认证（「个人信息」→「实名认证」）。</p>
          <label class="field">
            <span>收货地址</span>
            <textarea v-model="checkoutAddress" rows="3" placeholder="详细地址"></textarea>
          </label>
          <label class="field">
            <span>联系电话</span>
            <input v-model="checkoutPhone" type="text" placeholder="手机号" />
          </label>
          <div class="modal__actions">
            <button class="btn primary" type="button" :disabled="checkoutBusy" @click="submitCheckout">
              {{ checkoutBusy ? '提交中…' : '确认下单' }}
            </button>
            <button class="btn" type="button" :disabled="checkoutBusy" @click="checkoutOpen = false">取消</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 底部购物车条 -->
    <div class="cart-dock">
      <div class="cart-dock__inner">
        <div class="cart-dock__info">
          购物车 <strong>{{ cartCount }}</strong> 项 · 合计 <strong class="money">¥{{ cartTotal.toFixed(2) }}</strong>
        </div>
        <div class="cart-dock__actions">
          <button class="btn" type="button" @click="cartModalOpen = true">查看购物车</button>
          <button class="btn primary" type="button" :disabled="!cartLines.length" @click="openCheckout">结算</button>
        </div>
      </div>
    </div>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding-bottom: 88px;
}

.home-marquee {
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
  padding: 8px 16px 4px;
  box-sizing: border-box;
}

.home-marquee__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.home-marquee__label {
  font-size: 15px;
  font-weight: 900;
  letter-spacing: 0.02em;
  color: rgba(15, 23, 42, 0.88);
}

.home-marquee__hint {
  font-size: 12px;
  font-weight: 700;
  opacity: 0.55;
}

@media (prefers-color-scheme: dark) {
  .home-marquee__label {
    color: rgba(248, 250, 252, 0.92);
  }
}

.marquee-row {
  overflow: hidden;
  border-radius: 14px;
  margin-bottom: 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.45);
}

@media (prefers-color-scheme: dark) {
  .marquee-row {
    background: rgba(15, 23, 42, 0.22);
    border-color: rgba(148, 163, 184, 0.15);
  }
}

.marquee-track {
  display: flex;
  width: max-content;
  will-change: transform;
  animation: home-marquee-x 32s linear infinite;
}

.marquee-track--fast {
  animation-duration: 26s;
}

.marquee-track--slow {
  animation-duration: 38s;
}

.marquee-track.is-paused {
  animation-play-state: paused;
}

.marquee-group {
  display: flex;
  align-items: stretch;
  gap: 14px;
  padding: 10px 7px;
}

.marquee-card {
  position: relative;
  flex: 0 0 auto;
  width: 200px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
}

.marquee-card__img {
  display: block;
  width: 200px;
  height: 112px;
  object-fit: cover;
  vertical-align: middle;
}

.marquee-card__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px;
  text-align: center;
  background: rgba(15, 23, 42, 0.58);
  color: #fff;
  opacity: 0;
  transition: opacity 0.35s ease;
}

.marquee-card:hover .marquee-card__overlay,
.marquee-card:focus-within .marquee-card__overlay {
  opacity: 1;
}

.marquee-card__title {
  font-size: 14px;
  font-weight: 900;
  line-height: 1.25;
}

.marquee-card__sub {
  font-size: 11px;
  font-weight: 700;
  opacity: 0.92;
  line-height: 1.35;
  max-width: 11em;
}

@keyframes home-marquee-x {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .marquee-track {
    animation: none;
    flex-wrap: wrap;
    width: 100%;
    max-width: 100%;
    justify-content: center;
  }

  .marquee-group[aria-hidden='true'] {
    display: none;
  }
}

.content {
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
  padding: 16px;
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
  align-items: start;
}

.sidebar {
  position: sticky;
  top: 76px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(8px);
  padding: 14px;
}

@media (prefers-color-scheme: dark) {
  .sidebar {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}

.sidebar__title {
  font-size: 14px;
  font-weight: 900;
  margin-bottom: 10px;
}
.sidebar__subTitle {
  font-size: 12px;
  font-weight: 900;
  opacity: 0.75;
  margin: 8px 0 8px;
}

.cats {
  display: grid;
  gap: 8px;
}

.cat {
  text-align: left;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.35);
  color: inherit;
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 800;
  opacity: 0.88;
}

.cat.active {
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12);
  background: rgba(99, 102, 241, 0.12);
  opacity: 1;
}

.main {
  min-width: 0;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.55);
}
@media (prefers-color-scheme: dark) {
  .search-bar {
    background: rgba(15, 23, 42, 0.35);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.search-bar__label {
  font-size: 13px;
  font-weight: 800;
  opacity: 0.75;
  flex-shrink: 0;
}
.search-bar__input {
  flex: 1;
  min-width: 0;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 14px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.85);
  color: inherit;
}
@media (prefers-color-scheme: dark) {
  .search-bar__input {
    background: rgba(2, 6, 23, 0.5);
    border-color: rgba(148, 163, 184, 0.2);
  }
}

.main__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 6px 14px;
}

.main__title {
  font-size: 18px;
  font-weight: 900;
}

.main__count {
  font-size: 13px;
  opacity: 0.7;
}

.empty-hint {
  min-height: 220px;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 10px;
  padding: 32px 20px;
  text-align: center;
  border-radius: 16px;
  border: 1px dashed rgba(15, 23, 42, 0.16);
  background: rgba(255, 255, 255, 0.45);
}
@media (prefers-color-scheme: dark) {
  .empty-hint {
    border-color: rgba(148, 163, 184, 0.22);
    background: rgba(15, 23, 42, 0.22);
  }
}
.empty-hint__text {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  line-height: 1.5;
  opacity: 0.88;
  max-width: 28rem;
}
.empty-hint__sub {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  opacity: 0.65;
  max-width: 26rem;
  line-height: 1.5;
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.card {
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(8px);
  display: grid;
  grid-template-rows: 180px 1fr;
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
.placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  font-size: 13px;
  opacity: 0.7;
}

.card__img img,
.card__img-el {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.card__img-el {
  cursor: zoom-in;
}
.card__img-el:focus-visible {
  outline: 2px solid rgba(99, 102, 241, 0.65);
  outline-offset: 2px;
}

.card__body {
  padding: 12px;
  display: grid;
  gap: 6px;
}

.card__badges {
  display: flex;
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

.card__name {
  font-weight: 900;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card__intro {
  font-size: 13px;
  opacity: 0.75;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 4px;
}

.card__btns {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.star-btn {
  width: auto;
  min-width: 2rem;
  height: auto;
  padding: 4px;
  margin: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  color: rgba(100, 116, 139, 0.85);
  font-size: 26px;
  line-height: 1;
  cursor: pointer;
  display: grid;
  place-items: center;
  -webkit-tap-highlight-color: transparent;
  transition: color 0.15s, transform 0.15s, opacity 0.15s;
}

.star-btn:hover {
  color: rgba(71, 85, 105, 0.95);
  transform: scale(1.08);
}

.star-btn--on {
  color: #f59e0b;
}

.star-btn--on:hover {
  color: #d97706;
  transform: scale(1.08);
}

.price {
  font-weight: 900;
  letter-spacing: 0.2px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  min-width: 0;
}

.price__rent-line {
  display: inline-flex;
  flex-wrap: nowrap;
  align-items: baseline;
  white-space: nowrap;
}

.unit {
  font-size: 12px;
  opacity: 0.75;
  margin-left: 1px;
}

.dep {
  font-size: 11px;
  font-weight: 700;
  opacity: 0.65;
  line-height: 1.2;
}

.btn {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.4);
  color: inherit;
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 800;
}

.btn.primary {
  border-color: rgba(99, 102, 241, 0.28);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.95), rgba(59, 130, 246, 0.95));
  color: white;
}

.btn--sm {
  padding: 6px 10px;
  font-size: 13px;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* modals */
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

.panel--wide {
  max-width: 520px;
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

.modal__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}

.money {
  color: #c2410c;
  font-size: 1.05em;
}

@media (prefers-color-scheme: dark) {
  .money {
    color: #fdba74;
  }
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

.cart-lines {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cart-line {
  padding: 10px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}
.cart-line__title {
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.cart-line__sub {
  font-size: 13px;
  opacity: 0.75;
  margin-top: 4px;
}
.cart-line__ctrl {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.days-label {
  font-weight: 800;
  min-width: 3rem;
  text-align: center;
}
.empty-cart {
  font-size: 14px;
  opacity: 0.65;
  padding: 12px 0;
}

.field {
  display: grid;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 800;
}
.field input,
.field textarea {
  font-weight: 500;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.6);
  color: inherit;
}
.hint {
  font-size: 13px;
  opacity: 0.7;
  margin: 0 0 12px;
}
.hint--muted {
  margin-top: -6px;
  font-size: 12px;
}

.identity-prompt {
  max-width: 420px;
}
.identity-prompt__text {
  margin: 0 0 10px;
  font-size: 14px;
  line-height: 1.55;
  opacity: 0.92;
}
.identity-prompt__sub {
  margin: 0 0 18px;
  font-size: 12px;
  line-height: 1.45;
  opacity: 0.72;
}
.identity-prompt__actions {
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

/* fixed dock */
.cart-dock {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1500;
  border-top: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px);
  box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.06);
}

@media (prefers-color-scheme: dark) {
  .cart-dock {
    background: rgba(15, 23, 42, 0.92);
    border-top-color: rgba(148, 163, 184, 0.2);
  }
}

.cart-dock__inner {
  max-width: 1240px;
  margin: 0 auto;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.cart-dock__actions {
  display: flex;
  gap: 10px;
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

@media (max-width: 980px) {
  .content {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: relative;
    top: auto;
  }

  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
