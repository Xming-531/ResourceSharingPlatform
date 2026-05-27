<script setup>
import { computed, onMounted, ref } from 'vue'
import { deleteBillingMessage, fetchMyBillingMessages } from '@/api/billing'
import { fetchOrderDetail } from '@/api/orders'
import { effectiveListingType, normalizeRentAndType } from '@/api/products'
import { formatOrderDateTime } from '@/utils/datetime'

const loading = ref(false)
const err = ref('')
const list = ref([])
const deletingId = ref(null)

const orderViewingId = ref(null)
const orderDetail = ref(null)
const orderDetailLoading = ref(false)
const equipmentDetailOpen = ref(false)
const equipmentDetail = ref(null)

const equipmentDetailIsSale = computed(() => {
  const eq = equipmentDetail.value
  if (!eq) return false
  return effectiveListingType(eq) === 'sale'
})

function kindLabel(k) {
  if (k === 'debit') return '扣费'
  if (k === 'credit') return '到账'
  return k
}

function typeLabel(o) {
  return o?.order_type === 'sale' ? '出售' : '租赁'
}

function orderItemDisplayTitle(eq, equipmentId) {
  if (!eq) return `商品 #${equipmentId}`
  const t = `${eq.brand || ''}${eq.brand && eq.model ? ' ' : ''}${eq.model || ''}`.trim()
  return t || eq.title || `商品 #${equipmentId}`
}

function orderItemTypeLine(eq) {
  if (!eq) return ''
  const { rentSell, type } = normalizeRentAndType(eq)
  return `${rentSell} · ${type}`
}

async function load() {
  loading.value = true
  err.value = ''
  try {
    const res = await fetchMyBillingMessages()
    if (!res?.ok) throw new Error(res?.message || '加载失败')
    list.value = res.data || []
  } catch (e) {
    err.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function onDelete(m) {
  if (!confirm('确定删除该条账单消息？删除后不可恢复。')) return
  deletingId.value = m.message_id
  err.value = ''
  try {
    const res = await deleteBillingMessage(m.message_id)
    if (!res?.ok) throw new Error(res?.message || '删除失败')
    list.value = list.value.filter((x) => x.message_id !== m.message_id)
  } catch (e) {
    err.value = e?.message || '删除失败'
  } finally {
    deletingId.value = null
  }
}

async function onViewOrder(orderId) {
  if (orderId == null || orderId === '') return
  orderViewingId.value = Number(orderId)
  orderDetail.value = null
  orderDetailLoading.value = true
  try {
    const res = await fetchOrderDetail(orderViewingId.value)
    if (!res?.ok) throw new Error(res?.message || '加载失败')
    orderDetail.value = res.data
  } catch (e) {
    alert(e?.message || '加载失败')
    orderViewingId.value = null
  } finally {
    orderDetailLoading.value = false
  }
}

function closeOrderDetail() {
  orderViewingId.value = null
  orderDetail.value = null
  equipmentDetailOpen.value = false
  equipmentDetail.value = null
}

function openEquipmentDetail(eq) {
  if (!eq) {
    alert('暂无商品信息')
    return
  }
  equipmentDetail.value = eq
  equipmentDetailOpen.value = true
}

function closeEquipmentDetail() {
  equipmentDetailOpen.value = false
  equipmentDetail.value = null
}

onMounted(load)
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">账单消息</div>
      <div class="sub">模拟平台监管账户：记录下单扣费与交易完成后的结算说明。</div>
      <button class="btn" type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button>
    </div>

    <p v-if="err" class="err">{{ err }}</p>

    <div class="table">
      <div class="tr th">
        <div>时间</div>
        <div>类型</div>
        <div>金额</div>
        <div>编号</div>
        <div>备注</div>
        <div>操作</div>
      </div>
      <div v-if="loading" class="tr"><div class="tr__full">加载中...</div></div>
      <div v-else-if="!list.length" class="tr tr--empty"><div class="tr__full">暂无账单消息（下单或完成交易后将在此展示）。</div></div>
      <template v-else>
        <div v-for="m in list" :key="m.message_id" class="tr">
          <div class="mono">{{ m.created_at?.replace('T', ' ').slice(0, 19) }}</div>
          <div>
            <span class="tag" :class="m.kind === 'debit' ? 'tag--debit' : 'tag--credit'">{{ kindLabel(m.kind) }}</span>
          </div>
          <div class="money" :class="m.kind === 'debit' ? 'money--debit' : 'money--credit'">
            {{ m.kind === 'debit' ? '−' : '+' }}¥{{ m.amount }}
          </div>
          <div class="ids-col">
            <div>
              <span class="ids-col__name">消息编号</span>
              <span class="mono ids-col__num">{{ m.message_id }}</span>
            </div>
            <div>
              <span class="ids-col__name">关联订单号</span>
              <span class="mono ids-col__num">{{ m.order_id != null ? m.order_id : '无' }}</span>
            </div>
          </div>
          <div class="remark">{{ m.remark }}</div>
          <div class="ops">
            <button
              v-if="m.order_id != null"
              class="btn btn--order"
              type="button"
              @click="onViewOrder(m.order_id)"
            >
              订单
            </button>
            <button
              class="btn btn--danger"
              type="button"
              :disabled="deletingId === m.message_id"
              @click="onDelete(m)"
            >
              {{ deletingId === m.message_id ? '删除中…' : '删除' }}
            </button>
          </div>
        </div>
      </template>
    </div>

    <Teleport to="body">
      <div v-if="orderViewingId != null" class="modal" role="dialog" aria-modal="true">
        <div class="backdrop" @click="closeOrderDetail"></div>
        <div class="panel">
          <div class="panel__head">
            <div class="panel__title">订单详情 #{{ orderViewingId }}</div>
            <button class="btn" type="button" @click="closeOrderDetail">关闭</button>
          </div>
          <div v-if="orderDetailLoading" class="muted">加载中...</div>
          <div v-else-if="orderDetail" class="panel__body">
            <div class="kv">
              <div class="k">类型</div><div class="v">{{ typeLabel(orderDetail) }}</div>
              <div class="k">状态</div><div class="v">{{ orderDetail.status }}</div>
              <div class="k">金额</div><div class="v">¥{{ orderDetail.total_amount }}</div>
              <div class="k">买家</div>
              <div class="v">{{ orderDetail.buyer?.username || ('用户 #' + orderDetail.user_id) }}</div>
              <div class="k">卖家</div>
              <div class="v">{{ orderDetail.owner?.username || ('用户 #' + orderDetail.owner_id) }}</div>
              <div class="k">地址</div><div class="v">{{ orderDetail.shipping_address }}</div>
              <div class="k">电话</div><div class="v mono">{{ orderDetail.contact_phone }}</div>
              <div class="k">创建</div><div class="v">{{ formatOrderDateTime(orderDetail.created_at) }}</div>
              <template v-if="orderDetail.order_type === 'rent' && orderDetail.status === '待归还'">
                <div class="k">归还确认</div>
                <div class="v">
                  <span :class="{ 'text-ok': orderDetail.buyer_return_ok }">{{
                    orderDetail.buyer_return_ok ? '买家已确认' : '买家待确认'
                  }}</span>
                  <span class="sep">·</span>
                  <span :class="{ 'text-ok': orderDetail.owner_return_ok }">{{
                    orderDetail.owner_return_ok ? '卖家已确认' : '卖家待确认'
                  }}</span>
                </div>
              </template>
            </div>
            <div v-if="orderDetail.items?.length" class="items">
              <div class="items__title">订单明细</div>
              <div v-for="it in orderDetail.items" :key="it.order_item_id" class="it">
                <div class="it__head">
                  <div>
                    <div class="mono">item#{{ it.order_item_id }} · {{ orderItemDisplayTitle(it.equipment, it.equipment_id) }}</div>
                    <div v-if="it.equipment && orderItemTypeLine(it.equipment)" class="muted it__sub">
                      {{ orderItemTypeLine(it.equipment) }}
                    </div>
                  </div>
                  <button
                    v-if="it.equipment"
                    class="btn btn--sm"
                    type="button"
                    @click="openEquipmentDetail(it.equipment)"
                  >
                    商品详情
                  </button>
                </div>
                <div class="muted">
                  天数 {{ it.rental_days }} · 单价/日租金 ¥{{ it.rental_price }} · 小计 ¥{{ it.subtotal }} · 押金 ¥{{
                    it.deposit_amount
                  }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="equipmentDetailOpen && equipmentDetail" class="modal modal--eq" role="dialog" aria-modal="true">
        <div class="backdrop" @click="closeEquipmentDetail"></div>
        <div class="panel panel--eq">
          <div class="panel__head">
            <div class="panel__title">商品详情</div>
            <button class="btn" type="button" @click="closeEquipmentDetail">关闭</button>
          </div>
          <div class="eq-detail">
            <div v-if="equipmentDetail.cover_img_url" class="eq-cover">
              <img :src="equipmentDetail.cover_img_url" alt="封面" />
            </div>
            <div class="kv kv--eq">
              <div class="k">展示名</div>
              <div class="v">{{ orderItemDisplayTitle(equipmentDetail, equipmentDetail.equipment_id) }}</div>
              <div class="k">租售 / 类型</div>
              <div class="v">{{ orderItemTypeLine(equipmentDetail) || '—' }}</div>
              <div class="k">分类</div>
              <div class="v">{{ equipmentDetail.category }}</div>
              <div class="k">品牌/型号</div>
              <div class="v">{{ equipmentDetail.brand }} {{ equipmentDetail.model }}</div>
              <div class="k">描述</div>
              <div class="v desc">{{ equipmentDetail.description }}</div>
              <div class="k">价格</div>
              <div class="v">
                ¥{{ equipmentDetail.price
                }}<template v-if="!equipmentDetailIsSale">（日租金）</template>
              </div>
              <div class="k">押金</div>
              <div class="v">¥{{ equipmentDetail.deposit }}</div>
              <div class="k">位置</div>
              <div class="v">{{ equipmentDetail.location }}</div>
              <div class="k">状态</div>
              <div class="v">{{ equipmentDetail.status }}</div>
              <template v-if="equipmentDetail.owner">
                <div class="k">卖家</div>
                <div class="v">{{ equipmentDetail.owner.username || equipmentDetail.owner_id }}</div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.page {
  padding: 4px;
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
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn--order {
  border-color: rgba(99, 102, 241, 0.45);
  background: rgba(99, 102, 241, 0.12);
}
.btn--danger {
  border-color: rgba(220, 38, 38, 0.4);
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}
@media (prefers-color-scheme: dark) {
  .btn--danger {
    color: #fecaca;
  }
}
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
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
.tr {
  display: grid;
  grid-template-columns: 150px 72px 100px minmax(132px, 0.85fr) minmax(160px, 1.2fr) minmax(148px, auto);
  gap: 10px;
  align-items: start;
  padding: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}
.ids-col {
  display: grid;
  gap: 6px;
  font-size: 12px;
  line-height: 1.35;
}
.ids-col__name {
  font-weight: 800;
  opacity: 0.62;
  margin-right: 6px;
}
.ids-col__num {
  font-size: 12px;
}
.tr.th {
  border-top: 0;
  font-weight: 900;
  background: rgba(148, 163, 184, 0.14);
  align-items: center;
}
.tr__full {
  grid-column: 1 / -1;
}
.tr--empty .tr__full {
  opacity: 0.72;
  font-size: 14px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
  font-size: 12px;
}
.money {
  font-weight: 900;
  font-size: 14px;
}
.money--debit {
  color: #b45309;
}
.money--credit {
  color: #15803d;
}
@media (prefers-color-scheme: dark) {
  .money--debit {
    color: #fbbf24;
  }
  .money--credit {
    color: #86efac;
  }
}
.tag {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}
.tag--debit {
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.35);
}
.tag--credit {
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.35);
}
.remark {
  font-size: 13px;
  line-height: 1.45;
  opacity: 0.88;
}
@media (max-width: 900px) {
  .tr {
    grid-template-columns: 1fr;
  }
  .tr.th {
    display: none;
  }
}

.muted {
  font-size: 13px;
  opacity: 0.65;
}
.text-ok {
  color: #15803d;
  font-weight: 900;
}
@media (prefers-color-scheme: dark) {
  .text-ok {
    color: #86efac;
  }
}
.sep {
  margin: 0 6px;
  opacity: 0.45;
}

.modal {
  position: fixed;
  inset: 0;
  z-index: 2000;
}
.backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
}
.panel {
  position: relative;
  margin: 10vh auto 0;
  max-width: 720px;
  width: calc(100% - 32px);
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.98);
  padding: 14px;
}
@media (prefers-color-scheme: dark) {
  .panel {
    background: rgba(15, 23, 42, 0.96);
    border-color: rgba(148, 163, 184, 0.2);
  }
}
.panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}
.panel__title {
  font-size: 16px;
  font-weight: 900;
}
.kv {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 8px 10px;
  font-size: 13px;
}
.k {
  opacity: 0.7;
  font-weight: 800;
}
.v {
  font-weight: 800;
}
.items {
  margin-top: 12px;
}
.items__title {
  font-weight: 900;
  margin-bottom: 8px;
}
.it {
  padding: 8px 0;
  border-top: 1px dashed rgba(15, 23, 42, 0.12);
}
.it__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 4px;
}
.it__sub {
  font-size: 12px;
  margin-top: 2px;
}
.btn--sm {
  padding: 6px 10px;
  font-size: 12px;
  flex-shrink: 0;
}
.modal--eq {
  z-index: 2100;
}
.panel--eq {
  max-width: 480px;
}
.eq-detail {
  padding-top: 4px;
}
.eq-cover {
  margin-bottom: 12px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(2, 6, 23, 0.06);
}
.eq-cover img {
  display: block;
  width: 100%;
  max-height: 220px;
  object-fit: contain;
}
.kv--eq {
  grid-template-columns: 100px 1fr;
}
.kv--eq .desc {
  white-space: pre-wrap;
  line-height: 1.5;
  font-weight: 600;
}
</style>
