<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  adminApproveProduct,
  adminDeleteProduct,
  adminListProducts,
  adminRejectProduct,
  adminToggleProductOnline,
} from '@/api/admin'

const route = useRoute()

const resources = ref([])
const loading = ref(false)
const viewing = ref(null)

const filterStatus = ref('')

function canAdminApprove(r) {
  return r.status === '待审核'
}
function canAdminReject(r) {
  return r.status === '待审核'
}
function canAdminOffShelf(r) {
  return r.status === '已上架'
}

const viewInfo = computed(() => {
  const r = viewing.value
  const raw = r?.raw || {}
  if (!r) return null
  const c = (raw.category || '').trim()
  const isRentSellCat = c === '出租' || c === '出售'
  const rentSell = isRentSellCat ? c : raw.listing_type === 'sale' ? '出售' : '出租'
  const productType = isRentSellCat ? raw.title || '' : c || raw.title || ''
  return {
    id: r.id,
    ownerUsername: raw.owner?.username || r.owner,
    rentSell,
    name: `${raw.brand || ''}${raw.brand && raw.model ? ' ' : ''}${raw.model || ''}`.trim() || raw.title || '',
    type: productType,
    brand: raw.brand || '',
    model: raw.model || '',
    description: raw.description || '',
    price: raw.price ?? '',
    deposit: raw.deposit ?? '',
    location: raw.location || '',
    status: raw.status || r.status,
    cover: raw.cover_img_url || '',
    createdAt: raw.created_at || '',
  }
})

async function reload() {
  loading.value = true
  try {
    const res = await adminListProducts({ status: filterStatus.value || undefined })
    resources.value = res?.data || []
  } catch (e) {
    alert(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const s = route.query.status
  if (typeof s === 'string' && s) filterStatus.value = s
  reload()
})

async function onApprove(r) {
  try {
    await adminApproveProduct(r.id)
    await reload()
  } catch (e) {
    alert(e?.message || '审核失败')
  }
}

async function onReject(r) {
  try {
    if (!canAdminReject(r)) return
    if (!confirm(`确定驳回资源「${r.title}」的上架申请？`)) return
    await adminRejectProduct(r.id)
    await reload()
  } catch (e) {
    alert(e?.message || '操作失败')
  }
}

async function onOffShelfAdmin(r) {
  try {
    if (!canAdminOffShelf(r)) return
    await adminToggleProductOnline(r.id, false)
    await reload()
  } catch (e) {
    alert(e?.message || '操作失败')
  }
}

async function onDelete(r) {
  if (r.status !== '已下架' && r.status !== '已卖出') return
  if (!confirm(`确定删除资源「${r.title}」？删除后不可恢复。`)) return
  try {
    await adminDeleteProduct(r.id)
    if (viewing.value?.id === r.id) closeView()
    await reload()
  } catch (e) {
    alert(e?.message || '删除失败')
  }
}

function onView(r) {
  viewing.value = r
}

function closeView() {
  viewing.value = null
}
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">总体资源管理</div>
      <div class="sub">
        「待审核」可通过或驳回；「已上架」可下架；删除仅允许「已下架」或「已卖出」。
      </div>
    </div>

    <div class="toolbar">
      <label class="toolbar__label" for="res-status-filter">状态筛选</label>
      <select id="res-status-filter" v-model="filterStatus" class="filter-select" @change="reload">
        <option value="">全部</option>
        <option value="待审核">待审核</option>
        <option value="已上架">已上架</option>
        <option value="已驳回">已驳回</option>
        <option value="已下架">已下架</option>
        <option value="已撤回">已撤回</option>
        <option value="待交付">待交付</option>
        <option value="待取货">待取货</option>
        <option value="租赁中">租赁中</option>
        <option value="已卖出">已卖出</option>
      </select>
    </div>

    <div class="table">
      <div class="tr th">
        <div>资源名称</div>
        <div>发布者</div>
        <div>状态</div>
        <div>操作</div>
      </div>
      <div v-if="loading" class="tr"><div>加载中...</div></div>
      <div v-for="r in resources" :key="r.id" class="tr">
        <div class="name">{{ r.title }}</div>
        <div class="mono">{{ r.owner }}</div>
        <div><span class="tag">{{ r.status }}</span></div>
        <div class="ops">
          <button class="btn" type="button" @click="onView(r)">查看</button>
          <button class="btn" type="button" :disabled="!canAdminApprove(r)" @click="onApprove(r)">审核通过</button>
          <button class="btn" type="button" :disabled="!canAdminReject(r)" @click="onReject(r)">驳回</button>
          <button
            class="btn"
            type="button"
            :disabled="!canAdminOffShelf(r)"
            title="仅已上架资源可下架"
            @click="onOffShelfAdmin(r)"
          >
            下架
          </button>
          <button
            class="btn btn--danger"
            type="button"
            :disabled="r.status !== '已下架' && r.status !== '已卖出'"
            title="仅已下架或已卖出可删除"
            @click="onDelete(r)"
          >
            删除
          </button>
        </div>
      </div>
    </div>

    <div v-if="viewInfo" class="modal" role="dialog" aria-modal="true">
      <div class="backdrop" @click="closeView"></div>
      <div class="panel">
        <div class="panel__head">
          <div class="panel__title">资源信息</div>
          <button class="btn" type="button" @click="closeView">关闭</button>
        </div>

        <div class="panel__body">
          <div class="kv">
            <div class="k">发布者</div><div class="v mono">{{ viewInfo.ownerUsername }}</div>
            <div class="k">租售（category）</div><div class="v">{{ viewInfo.rentSell }}</div>
            <div class="k">商品类型（title）</div><div class="v">{{ viewInfo.type }}</div>
            <div class="k">展示名称</div><div class="v">{{ viewInfo.name }}</div>
            <div class="k">品牌/型号</div><div class="v">{{ viewInfo.brand }} {{ viewInfo.model }}</div>
            <div class="k">价格</div><div class="v">¥{{ viewInfo.price }}</div>
            <div class="k">押金</div><div class="v">¥{{ viewInfo.deposit }}</div>
            <div class="k">所在地</div><div class="v">{{ viewInfo.location }}</div>
            <div class="k">状态</div><div class="v">{{ viewInfo.status }}</div>
            <div class="k">创建时间</div><div class="v mono">{{ viewInfo.createdAt }}</div>
          </div>

          <div v-if="viewInfo.description" class="desc">
            <div class="desc__title">描述</div>
            <div class="desc__text">{{ viewInfo.description }}</div>
          </div>

          <div class="cover">
            <div class="desc__title">封面</div>
            <div v-if="viewInfo.cover" class="cover__img">
              <img :src="viewInfo.cover" alt="cover" />
            </div>
            <div v-else class="cover__empty">暂无封面</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.page {
  padding: 4px;
}
.head {
  padding: 6px 6px 14px;
}
.title {
  font-size: 18px;
  font-weight: 900;
}
.sub {
  font-size: 13px;
  opacity: 0.7;
  margin-top: 4px;
}
.table {
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  overflow: hidden;
}
@media (prefers-color-scheme: dark) {
  .table {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 0 6px 12px;
}
.toolbar__label {
  font-size: 13px;
  font-weight: 800;
  opacity: 0.85;
}
.filter-select {
  min-width: 160px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.5);
  color: inherit;
  padding: 8px 12px;
  font-weight: 700;
  cursor: pointer;
}
@media (prefers-color-scheme: dark) {
  .filter-select {
    background: rgba(15, 23, 42, 0.45);
    border-color: rgba(148, 163, 184, 0.22);
  }
}
.tr {
  display: grid;
  grid-template-columns: 1fr 140px 140px minmax(260px, 1fr);
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}
.tr.th {
  border-top: 0;
  font-weight: 900;
  background: rgba(148, 163, 184, 0.14);
}
.name {
  font-weight: 900;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}
.tag {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(34, 197, 94, 0.25);
  background: rgba(34, 197, 94, 0.1);
  font-weight: 800;
}
.ops {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
.btn {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.4);
  color: inherit;
  border-radius: 12px;
  padding: 8px 10px;
  cursor: pointer;
  font-weight: 800;
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn--danger {
  border-color: rgba(220, 38, 38, 0.35);
  background: rgba(220, 38, 38, 0.08);
}

.modal {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 18px;
}
.backdrop {
  position: absolute;
  inset: 0;
  background: rgba(2, 6, 23, 0.55);
}
.panel {
  position: relative;
  width: min(860px, 100%);
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  overflow: hidden;
}
@media (prefers-color-scheme: dark) {
  .panel {
    background: rgba(15, 23, 42, 0.82);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}
.panel__title {
  font-weight: 900;
}
.panel__body {
  padding: 14px;
  display: grid;
  gap: 14px;
}
.kv {
  display: grid;
  grid-template-columns: 120px 1fr 120px 1fr;
  gap: 10px 12px;
  align-items: baseline;
}
.k {
  font-size: 12px;
  opacity: 0.75;
  font-weight: 900;
}
.v {
  font-weight: 800;
}
.desc__title {
  font-size: 12px;
  opacity: 0.75;
  font-weight: 900;
  margin-bottom: 6px;
}
.desc__text {
  font-size: 13px;
  opacity: 0.9;
  line-height: 1.6;
  white-space: pre-wrap;
}
.cover__img img {
  width: 100%;
  max-height: 360px;
  object-fit: contain;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(2, 6, 23, 0.06);
}
.cover__empty {
  font-size: 13px;
  opacity: 0.7;
}
@media (max-width: 720px) {
  .kv {
    grid-template-columns: 110px 1fr;
  }
}
@media (max-width: 980px) {
  .tr {
    grid-template-columns: 1fr;
  }
  .tr.th {
    display: none;
  }
  .ops {
    justify-content: flex-start;
  }
}
</style>

