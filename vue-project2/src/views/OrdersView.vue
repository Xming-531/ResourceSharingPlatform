<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  confirmHandoverBuyer,
  confirmHandoverOwner,
  confirmReturnBuyer,
  confirmReturnOwner,
  deleteAdminOrder,
  deleteOrder,
  fetchAdminOrderDetail,
  fetchAdminOrders,
  fetchMyOrders,
  fetchOrderDetail,
  fetchSalesOrders,
  rejectEarlyReturnOwner,
  requestEarlyReturn,
  requestEarlyReturnOwner,
  requestNormalReturn,
  confirmNormalReturnOwner,
  requestOverdueReturn,
} from '@/api/orders'
import { effectiveListingType, normalizeRentAndType } from '@/api/products'
import { formatOrderDateTime, formatOverdueFromSeconds, formatRentalRemaining } from '@/utils/datetime'
import { isAdmin } from '@/utils/session'

const loading = ref(false)
const buyerOrders = ref([])
const sellerOrders = ref([])
const err = ref('')
const adminOrders = ref([])
const adminViewing = ref(null)
const adminDetail = ref(null)
const adminFilterStatus = ref('')
const adminFilterType = ref('')
const adminQ = ref('')

const userOrderViewing = ref(null)
const userOrderDetail = ref(null)
const userOrderDetailLoading = ref(false)
const equipmentDetail = ref(null)
const equipmentDetailOpen = ref(false)

/** 普通用户：买到 / 卖出 / 租到 / 租出 */
const userOrderTab = ref('bought')

const isAdminUser = computed(() => isAdmin())

const ordersBought = computed(() => buyerOrders.value.filter((o) => o.order_type === 'sale'))
const ordersRentIn = computed(() => buyerOrders.value.filter((o) => o.order_type === 'rent'))
const ordersSold = computed(() => sellerOrders.value.filter((o) => o.order_type === 'sale'))
const ordersRentOut = computed(() => sellerOrders.value.filter((o) => o.order_type === 'rent'))

const userOrderTabs = computed(() => [
  { id: 'bought', label: '买到', list: ordersBought.value, role: 'buyer' },
  { id: 'sold', label: '卖出', list: ordersSold.value, role: 'seller' },
  { id: 'rentIn', label: '租到', list: ordersRentIn.value, role: 'buyer' },
  { id: 'rentOut', label: '租出', list: ordersRentOut.value, role: 'seller' },
])

const equipmentDetailIsSale = computed(() => {
  const eq = equipmentDetail.value
  if (!eq) return false
  return effectiveListingType(eq) === 'sale'
})

/** 每分钟刷新一次，用于租赁倒计时文案 */
const countdownTick = ref(0)
let countdownTimer

async function load() {
  loading.value = true
  err.value = ''
  try {
    if (isAdminUser.value) {
      const res = await fetchAdminOrders({
        status: adminFilterStatus.value || undefined,
        order_type: adminFilterType.value || undefined,
        q: adminQ.value || undefined,
      })
      if (!res?.ok) throw new Error(res?.message || '加载管理员订单失败')
      adminOrders.value = res.data || []
    } else {
      const [b, s] = await Promise.all([fetchMyOrders(), fetchSalesOrders()])
      if (!b?.ok) throw new Error(b?.message || '加载买家订单失败')
      if (!s?.ok) throw new Error(s?.message || '加载卖家订单失败')
      buyerOrders.value = b.data || []
      sellerOrders.value = s.data || []
    }
  } catch (e) {
    err.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  countdownTimer = setInterval(() => {
    countdownTick.value += 1
  }, 60_000)
})

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})

function typeLabel(o) {
  return o.order_type === 'sale' ? '出售' : '租赁'
}

function billingKindLabel(kind) {
  if (kind === 'debit') return '扣费'
  if (kind === 'credit') return '到账'
  return String(kind || '')
}

function billingRecipientLabel(m, order) {
  if (!m || !order) return ''
  const uid = Number(m.user_id)
  if (uid === Number(order.user_id)) return '买家'
  if (uid === Number(order.owner_id)) return '卖家'
  return `用户 #${m.user_id}`
}

async function viewAdminOrder(o) {
  adminViewing.value = o
  adminDetail.value = null
  try {
    const res = await fetchAdminOrderDetail(o.order_id)
    if (!res?.ok) throw new Error(res?.message || '加载详情失败')
    adminDetail.value = res.data
  } catch (e) {
    alert(e?.message || '加载失败')
  }
}

function closeAdminDetail() {
  adminViewing.value = null
  adminDetail.value = null
  equipmentDetailOpen.value = false
  equipmentDetail.value = null
}

async function viewUserOrder(o) {
  userOrderViewing.value = o
  userOrderDetail.value = null
  userOrderDetailLoading.value = true
  try {
    const res = await fetchOrderDetail(o.order_id)
    if (!res?.ok) throw new Error(res?.message || '加载失败')
    userOrderDetail.value = res.data
  } catch (e) {
    alert(e?.message || '加载失败')
    userOrderViewing.value = null
  } finally {
    userOrderDetailLoading.value = false
  }
}

function closeUserOrderDetail() {
  userOrderViewing.value = null
  userOrderDetail.value = null
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

async function onOwnerHandover(id) {
  try {
    const r = await confirmHandoverOwner(id)
    if (!r?.ok) throw new Error(r?.message || '操作失败')
    await load()
  } catch (e) {
    alert(e?.message || '失败')
  }
}

async function onBuyerHandover(id) {
  try {
    const r = await confirmHandoverBuyer(id)
    if (!r?.ok) throw new Error(r?.message || '操作失败')
    await load()
  } catch (e) {
    alert(e?.message || '失败')
  }
}

async function onReturnDone(id) {
  try {
    const r = await confirmReturnOwner(id)
    if (!r?.ok) throw new Error(r?.message || '操作失败')
    await load()
  } catch (e) {
    alert(e?.message || '失败')
  }
}

async function onBuyerReturn(id) {
  try {
    const r = await confirmReturnBuyer(id)
    if (!r?.ok) throw new Error(r?.message || '操作失败')
    await load()
  } catch (e) {
    alert(e?.message || '失败')
  }
}

async function onEarlyReturnBuyer(id) {
  try {
    const r = await requestEarlyReturn(id)
    if (!r?.ok) throw new Error(r?.message || '操作失败')
    await load()
  } catch (e) {
    alert(e?.message || '失败')
  }
}

async function onEarlyReturnOwner(id) {
  try {
    const r = await requestEarlyReturnOwner(id)
    if (!r?.ok) throw new Error(r?.message || '操作失败')
    await load()
  } catch (e) {
    alert(e?.message || '失败')
  }
}

async function onEarlyReturnOwnerReject(id) {
  if (!confirm('确定驳回该提前归还申请？驳回后租借方可再次发起申请。')) return
  try {
    const r = await rejectEarlyReturnOwner(id)
    if (!r?.ok) throw new Error(r?.message || '操作失败')
    await load()
  } catch (e) {
    alert(e?.message || '失败')
  }
}

async function onRequestNormalReturn(id) {
  try {
    const r = await requestNormalReturn(id)
    if (!r?.ok) throw new Error(r?.message || '操作失败')
    await load()
  } catch (e) {
    alert(e?.message || '失败')
  }
}

async function onConfirmNormalReturnOwner(id) {
  try {
    const r = await confirmNormalReturnOwner(id)
    if (!r?.ok) throw new Error(r?.message || '操作失败')
    await load()
  } catch (e) {
    alert(e?.message || '失败')
  }
}

async function onRequestOverdueReturn(id) {
  try {
    const r = await requestOverdueReturn(id)
    if (!r?.ok) throw new Error(r?.message || '操作失败')
    await load()
  } catch (e) {
    alert(e?.message || '失败')
  }
}

function buyerActions(o) {
  const actions = []
  if (
    (o.status === '待取货' || o.status === '待交付') &&
    !o.buyer_handover_ok &&
    o.owner_handover_ok
  ) {
    actions.push({ label: '买家确认已取货/收货', fn: () => onBuyerHandover(o.order_id) })
  }
  if (o.status === '待归还' && !o.buyer_return_ok) {
    actions.push({ label: '确认归还', fn: () => onBuyerReturn(o.order_id) })
  }
  return actions
}

function sellerActions(o) {
  const actions = []
  if ((o.status === '待取货' || o.status === '待交付') && !o.owner_handover_ok) {
    actions.push({ label: '卖家确认已交接', fn: () => onOwnerHandover(o.order_id) })
  }
  if (o.status === '待归还' && !o.owner_return_ok) {
    actions.push({ label: '确认归还', fn: () => onReturnDone(o.order_id) })
  }
  return actions
}

function canDeleteOrder(o) {
  return o.status === '已完成'
}

/** 租期结束时刻：与后端一致，优先租赁日程 rental_period_end_at，无日程时用 contract_due_at */
function orderLeaseEndIso(o) {
  return o.rental_period_end_at || o.contract_due_at || ''
}

function orderShowRentalCountdown(o) {
  return (
    o.order_type === 'rent' &&
    !!orderLeaseEndIso(o) &&
    (o.status === '租赁中' || o.status === '待归还')
  )
}

function rentalCountdownLabel(o) {
  void countdownTick.value
  return formatRentalRemaining(orderLeaseEndIso(o))
}

function isRentActive(o) {
  return o.order_type === 'rent' && o.status === '租赁中'
}

/**
 * 是否已超过约定租期结束（优先 rental_period_end_at，无则 contract_due_at；与后端 _is_past_rental_end 一致）。
 */
function rentalOverdue(o) {
  if (o.order_type !== 'rent') return false
  void countdownTick.value
  const endIso = orderLeaseEndIso(o)
  if (endIso) {
    const end = new Date(endIso).getTime()
    if (!Number.isNaN(end) && Date.now() >= end) return true
  }
  return !!o.rental_overdue
}

function showEarlyReturnBuyerBtn(o) {
  return (
    isRentActive(o) &&
    !rentalOverdue(o) &&
    !!o.early_return_allowed &&
    !o.early_return_buyer_agreed
  )
}

function earlyReturnBuyerWaitingSeller(o) {
  return isRentActive(o) && !rentalOverdue(o) && o.early_return_buyer_agreed && !o.early_return_owner_agreed
}

/** 仅租借方已申请提前归还后，出租方才可同意 */
function showEarlyReturnSellerBtn(o) {
  return isRentActive(o) && !rentalOverdue(o) && o.early_return_buyer_agreed && !o.early_return_owner_agreed
}

/** 租借方：在归还窗口内且尚未发起（超期后仅走待归还确认） */
function showNormalReturnBuyerBtn(o) {
  return (
    isRentActive(o) &&
    !rentalOverdue(o) &&
    o.normal_return_allowed &&
    !o.normal_return_buyer_requested
  )
}

/** 出租方：租借方已发起按时归还 */
function showNormalReturnOwnerBtn(o) {
  return isRentActive(o) && !rentalOverdue(o) && o.normal_return_buyer_requested
}

/** 租赁中且已超期：租借方点「超期归还」进待归还 */
function showOverdueReturnBuyerBtn(o) {
  return isRentActive(o) && rentalOverdue(o)
}

function overdueDurationText(o) {
  void countdownTick.value
  return formatOverdueFromSeconds(o.overdue_seconds)
}

async function onDeleteUserOrder(o) {
  if (!canDeleteOrder(o)) return
  if (!confirm(`确定删除订单 #${o.order_id}？删除后不可恢复，双方列表中均不再显示。`)) return
  try {
    const r = await deleteOrder(o.order_id)
    if (!r?.ok) throw new Error(r?.message || '删除失败')
    await load()
  } catch (e) {
    alert(e?.message || '删除失败')
  }
}

async function onDeleteAdminOrder(o) {
  if (!canDeleteOrder(o)) return
  if (!confirm(`确定删除订单 #${o.order_id}？删除后不可恢复。`)) return
  try {
    const r = await deleteAdminOrder(o.order_id)
    if (!r?.ok) throw new Error(r?.message || '删除失败')
    if (adminViewing.value?.order_id === o.order_id) closeAdminDetail()
    await load()
  } catch (e) {
    alert(e?.message || '删除失败')
  }
}
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">订单管理</div>
      <div class="sub">
        <span v-if="isAdminUser">查看与管理全站订单（汇总+详情）。</span>
        <span v-else>订单按「买到、卖出、租到、租出」四类查看；列表在每次进入或操作后刷新。</span>
      </div>
      <button class="btn" type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button>
    </div>

    <p v-if="err" class="err">{{ err }}</p>

    <div v-if="isAdminUser" class="admin">
      <div class="filters">
        <input v-model.trim="adminQ" class="inp" placeholder="搜索：订单号/买家ID/卖家ID" />
        <select v-model="adminFilterType" class="inp">
          <option value="">全部类型</option>
          <option value="rent">租赁</option>
          <option value="sale">出售</option>
        </select>
        <input v-model.trim="adminFilterStatus" class="inp" placeholder="状态（如 待取货/待交付/租赁中/待归还/已完成）" />
        <button class="btn primary" type="button" :disabled="loading" @click="load">查询</button>
      </div>
      <div class="table">
        <div class="tr th">
          <div>订单号</div>
          <div>类型</div>
          <div>状态</div>
          <div>买家</div>
          <div>卖家</div>
          <div>金额</div>
          <div>操作</div>
        </div>
        <div v-for="o in adminOrders" :key="o.order_id" class="tr">
          <div class="mono">#{{ o.order_id }}</div>
          <div>{{ typeLabel(o) }}</div>
          <div><span class="tag">{{ o.status }}</span></div>
          <div class="mono">{{ o.buyer?.username || o.user_id }}</div>
          <div class="mono">{{ o.owner?.username || o.owner_id }}</div>
          <div class="money">¥{{ o.total_amount }}</div>
          <div class="admin-ops">
            <button class="btn" type="button" @click="viewAdminOrder(o)">查看详情</button>
            <button
              v-if="canDeleteOrder(o)"
              class="btn danger"
              type="button"
              @click="onDeleteAdminOrder(o)"
            >
              删除
            </button>
          </div>
        </div>
      </div>

      <Teleport to="body">
        <div v-if="adminViewing" class="modal" role="dialog" aria-modal="true">
          <div class="backdrop" @click="closeAdminDetail"></div>
          <div class="panel">
            <div class="panel__head">
              <div class="panel__title">订单详情 #{{ adminViewing.order_id }}</div>
              <button class="btn" type="button" @click="closeAdminDetail">关闭</button>
            </div>
            <div class="panel__scroll">
            <div v-if="!adminDetail" class="muted panel__loading">加载中...</div>
            <div v-else class="panel__body">
              <div class="kv">
                <div class="k">类型</div><div class="v">{{ typeLabel(adminDetail) }}</div>
                <div class="k">状态</div><div class="v">{{ adminDetail.status }}</div>
                <div class="k">买家</div><div class="v mono">{{ adminDetail.buyer?.username || adminDetail.user_id }}</div>
                <div class="k">卖家</div><div class="v mono">{{ adminDetail.owner?.username || adminDetail.owner_id }}</div>
                <div class="k">金额</div><div class="v">¥{{ adminDetail.total_amount }}</div>
                <div class="k">地址</div><div class="v">{{ adminDetail.shipping_address }}</div>
                <div class="k">电话</div><div class="v mono">{{ adminDetail.contact_phone }}</div>
                <div class="k">创建</div><div class="v">{{ formatOrderDateTime(adminDetail.created_at) }}</div>
              </div>
              <div class="items" v-if="adminDetail.items?.length">
                <div class="items__title">订单明细</div>
                <div v-for="it in adminDetail.items" :key="it.order_item_id" class="it">
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
              <div class="items billing-msgs">
                <div class="items__title">关联流水消息</div>
                <div v-if="!adminDetail.billing_messages?.length" class="muted billing-msgs__empty">
                  暂无与本订单关联的账单流水（下单或成交结算后会在此汇总）。
                </div>
                <div v-else class="billing-msgs__list">
                  <div v-for="m in adminDetail.billing_messages" :key="m.message_id" class="billing-msgs__row">
                    <div class="billing-msgs__meta">
                      <span class="mono billing-msgs__time">{{ formatOrderDateTime(m.created_at) }}</span>
                      <span
                        class="tag billing-msgs__kind"
                        :class="m.kind === 'debit' ? 'tag--debit' : 'tag--credit'"
                      >{{ billingKindLabel(m.kind) }}</span>
                      <span class="billing-msgs__who">{{ billingRecipientLabel(m, adminDetail) }}</span>
                    </div>
                    <div class="billing-msgs__amt" :class="m.kind === 'debit' ? 'amt--debit' : 'amt--credit'">
                      {{ m.kind === 'debit' ? '−' : '+' }}¥{{ m.amount }}
                    </div>
                    <div class="billing-msgs__remark">{{ m.remark }}</div>
                  </div>
                </div>
              </div>
              <div v-if="canDeleteOrder(adminDetail)" class="admin-detail-actions">
                <button class="btn danger" type="button" @click="onDeleteAdminOrder(adminViewing)">删除订单</button>
              </div>
            </div>
            </div>
          </div>
        </div>
      </Teleport>
    </div>

    <div v-else class="user-orders">
      <nav class="order-tabs" aria-label="订单分类">
        <button
          v-for="t in userOrderTabs"
          :key="t.id"
          type="button"
          class="order-tab"
          :class="{ 'order-tab--active': userOrderTab === t.id }"
          @click="userOrderTab = t.id"
        >
          {{ t.label }}
          <span class="order-tab__count">{{ t.list.length }}</span>
        </button>
      </nav>

      <div
        v-for="t in userOrderTabs"
        v-show="userOrderTab === t.id"
        :key="'panel-' + t.id"
        class="tab-panel"
      >
        <div v-if="!t.list.length && !loading" class="empty">该分类下暂无订单</div>
        <div v-for="o in t.list" :key="t.id + '-' + o.order_id" class="card">
          <div class="card__head">
            <span class="oid">#{{ o.order_id }}</span>
            <span class="tag">{{ typeLabel(o) }}</span>
            <span class="status">{{ o.status }}</span>
          </div>
          <div class="row">总额：<strong>¥{{ o.total_amount }}</strong></div>
          <div v-if="t.role === 'seller'" class="row muted">
            买家：{{ o.buyer?.username || ('用户 #' + o.user_id) }}
          </div>
          <div class="row muted">地址：{{ o.shipping_address }}</div>
          <div class="row muted">电话：{{ o.contact_phone }}</div>
          <div class="row muted">创建：{{ formatOrderDateTime(o.created_at) }}</div>
          <div class="acts">
            <button class="btn" type="button" @click="viewUserOrder(o)">订单详情</button>
          </div>
          <div v-if="orderShowRentalCountdown(o)" class="row countdown">{{ rentalCountdownLabel(o) }}</div>
          <div v-if="isRentActive(o) && rentalOverdue(o)" class="row muted hint hint--warn">
            已超期 {{ overdueDurationText(o) || '—' }}。请先由租借方点「超期归还」进入待归还，再双方确认归还；超期费按规则从押金结算。
          </div>
          <div
            v-if="o.order_type === 'rent' && rentalOverdue(o) && o.status === '待归还'"
            class="row muted hint hint--warn"
          >
            已超期 {{ overdueDurationText(o) || '—' }}。请双方确认归还；超期使用费按天向上取整从押金扣除（不超过已付押金总额）。
          </div>
          <div
            v-if="
              isRentActive(o) &&
              !rentalOverdue(o) &&
              !o.normal_return_buyer_requested &&
              !o.early_return_buyer_agreed
            "
            class="row muted hint"
          >
            距离租期结束仍大于 3 小时可申请「提前归还」（出租方同意后进入待归还，双方再确认归还）；
            最后 3 小时内可「按时归还」，出租方确认后订单直接完成。
          </div>
          <template v-if="t.role === 'buyer'">
            <div
              v-if="(o.status === '待取货' || o.status === '待交付') && !o.owner_handover_ok && !o.buyer_handover_ok"
              class="row muted hint"
            >
              请待出租方/卖方确认交接后，您再确认取货/收货。
            </div>
            <div v-if="showOverdueReturnBuyerBtn(o)" class="acts">
              <button class="btn primary" type="button" @click="onRequestOverdueReturn(o.order_id)">超期归还</button>
            </div>
            <div v-if="showNormalReturnBuyerBtn(o)" class="acts">
              <button class="btn primary" type="button" @click="onRequestNormalReturn(o.order_id)">按时归还</button>
            </div>
            <div
              v-else-if="isRentActive(o) && !rentalOverdue(o) && o.normal_return_buyer_requested"
              class="row muted hint"
            >
              已归还，待租出方确认
            </div>
            <div v-if="showEarlyReturnBuyerBtn(o)" class="acts">
              <button class="btn" type="button" @click="onEarlyReturnBuyer(o.order_id)">申请提前归还</button>
            </div>
            <div v-else-if="earlyReturnBuyerWaitingSeller(o)" class="row muted hint">您已申请提前归还，待出租方同意</div>
            <div v-if="buyerActions(o).length" class="acts">
              <button v-for="(a, i) in buyerActions(o)" :key="i" class="btn primary" type="button" @click="a.fn">
                {{ a.label }}
              </button>
            </div>
            <div v-else-if="o.status === '待归还' && o.buyer_return_ok" class="row return-done">买家已确认</div>
          </template>
          <template v-else>
            <div
              v-if="showNormalReturnOwnerBtn(o)"
              class="row muted hint"
            >
              客户已确认归还，请及时确认。
            </div>
            <div v-if="showNormalReturnOwnerBtn(o)" class="acts">
              <button class="btn primary" type="button" @click="onConfirmNormalReturnOwner(o.order_id)">确认归还</button>
            </div>
            <div v-if="showEarlyReturnSellerBtn(o)" class="acts">
              <button class="btn" type="button" @click="onEarlyReturnOwner(o.order_id)">同意提前归还</button>
              <button class="btn warn" type="button" @click="onEarlyReturnOwnerReject(o.order_id)">驳回申请</button>
            </div>
            <div
              v-else-if="isRentActive(o) && !rentalOverdue(o) && o.early_return_allowed && !o.early_return_buyer_agreed"
              class="row muted hint"
            >
              待租借方发起「申请提前归还」后，您可在此同意。
            </div>
            <div
              v-else-if="
                isRentActive(o) &&
                !rentalOverdue(o) &&
                o.normal_return_allowed &&
                !o.normal_return_buyer_requested &&
                !o.early_return_buyer_agreed
              "
              class="row muted hint"
            >
              最后 3 小时内租借方可发起「按时归还」，确认后您在此点击「确认归还」即可完成订单。
            </div>
            <div v-if="sellerActions(o).length" class="acts">
              <button v-for="(a, i) in sellerActions(o)" :key="i" class="btn primary" type="button" @click="a.fn">
                {{ a.label }}
              </button>
            </div>
            <div v-else-if="o.status === '待归还' && o.owner_return_ok" class="row return-done">卖家已确认</div>
          </template>
          <div v-if="canDeleteOrder(o)" class="acts">
            <button class="btn danger" type="button" @click="onDeleteUserOrder(o)">删除订单</button>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="userOrderViewing" class="modal" role="dialog" aria-modal="true">
        <div class="backdrop" @click="closeUserOrderDetail"></div>
        <div class="panel">
          <div class="panel__head">
            <div class="panel__title">订单详情 #{{ userOrderViewing.order_id }}</div>
            <button class="btn" type="button" @click="closeUserOrderDetail">关闭</button>
          </div>
          <div class="panel__scroll">
          <div v-if="userOrderDetailLoading" class="muted panel__loading">加载中...</div>
          <div v-else-if="userOrderDetail" class="panel__body">
            <div class="kv">
              <div class="k">类型</div><div class="v">{{ typeLabel(userOrderDetail) }}</div>
              <div class="k">状态</div><div class="v">{{ userOrderDetail.status }}</div>
              <div class="k">金额</div><div class="v">¥{{ userOrderDetail.total_amount }}</div>
              <div class="k">买家</div>
              <div class="v">{{ userOrderDetail.buyer?.username || ('用户 #' + userOrderDetail.user_id) }}</div>
              <div class="k">卖家</div>
              <div class="v">{{ userOrderDetail.owner?.username || ('用户 #' + userOrderDetail.owner_id) }}</div>
              <div class="k">地址</div><div class="v">{{ userOrderDetail.shipping_address }}</div>
              <div class="k">电话</div><div class="v mono">{{ userOrderDetail.contact_phone }}</div>
              <div class="k">创建</div><div class="v">{{ formatOrderDateTime(userOrderDetail.created_at) }}</div>
              <template v-if="userOrderDetail.order_type === 'rent' && userOrderDetail.status === '待归还'">
                <div class="k">归还确认</div>
                <div class="v">
                  <span :class="{ 'text-ok': userOrderDetail.buyer_return_ok }">{{
                    userOrderDetail.buyer_return_ok ? '买家已确认' : '买家待确认'
                  }}</span>
                  <span class="sep">·</span>
                  <span :class="{ 'text-ok': userOrderDetail.owner_return_ok }">{{
                    userOrderDetail.owner_return_ok ? '卖家已确认' : '卖家待确认'
                  }}</span>
                </div>
              </template>
            </div>
            <div v-if="userOrderDetail.items?.length" class="items">
              <div class="items__title">订单明细</div>
              <div v-for="it in userOrderDetail.items" :key="it.order_item_id" class="it">
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
          <div class="panel__scroll">
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
      </div>
    </Teleport>
  </section>
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
.user-orders {
  max-width: 720px;
}

.order-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 6px 14px;
}

.order-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.45);
  color: inherit;
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
  font-weight: 800;
  font-size: 13px;
}

.order-tab__count {
  font-size: 11px;
  font-weight: 900;
  opacity: 0.65;
  min-width: 1.25rem;
  text-align: center;
}

.order-tab--active {
  border-color: rgba(99, 102, 241, 0.45);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.18), rgba(59, 130, 246, 0.14));
}

@media (prefers-color-scheme: dark) {
  .order-tab {
    background: rgba(15, 23, 42, 0.35);
    border-color: rgba(148, 163, 184, 0.22);
  }
  .order-tab--active {
    border-color: rgba(129, 140, 248, 0.45);
    background: rgba(99, 102, 241, 0.22);
  }
}

.tab-panel {
  padding: 0 6px;
}
.empty {
  font-size: 14px;
  opacity: 0.65;
}
.card {
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  padding: 12px;
  margin-bottom: 10px;
}
@media (prefers-color-scheme: dark) {
  .card {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.card__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.oid {
  font-family: ui-monospace, monospace;
  font-weight: 900;
}
.tag {
  font-size: 12px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.25);
}
.status {
  font-size: 13px;
  font-weight: 800;
}
.row {
  font-size: 13px;
  margin-bottom: 4px;
}
.row.countdown {
  font-weight: 900;
  color: #b45309;
}
@media (prefers-color-scheme: dark) {
  .row.countdown {
    color: #fbbf24;
  }
}
.muted {
  opacity: 0.72;
}
.hint {
  font-size: 12px;
  line-height: 1.45;
}
.hint--warn {
  color: #9a3412;
  opacity: 1;
}
@media (prefers-color-scheme: dark) {
  .hint--warn {
    color: #fdba74;
  }
}
.return-done {
  font-size: 13px;
  font-weight: 800;
  color: #15803d;
  margin-top: 8px;
}
@media (prefers-color-scheme: dark) {
  .return-done {
    color: #86efac;
  }
}
.text-ok {
  font-weight: 800;
  color: #15803d;
}
@media (prefers-color-scheme: dark) {
  .text-ok {
    color: #86efac;
  }
}
.sep {
  opacity: 0.45;
  padding: 0 0.35em;
}
.acts {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
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
.btn.warn {
  border-color: rgba(180, 83, 9, 0.45);
  background: rgba(251, 191, 36, 0.2);
  color: #92400e;
}
@media (prefers-color-scheme: dark) {
  .btn.warn {
    border-color: rgba(251, 191, 36, 0.35);
    background: rgba(120, 53, 15, 0.35);
    color: #fde68a;
  }
}
.btn.danger {
  border: 1px solid rgba(220, 38, 38, 0.4);
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}
@media (prefers-color-scheme: dark) {
  .btn.danger {
    color: #fecaca;
  }
}
.admin-ops {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.admin-detail-actions {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}

.admin .filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 6px 6px 12px;
}
.inp {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.5);
  color: inherit;
  border-radius: 12px;
  padding: 10px 12px;
  font-weight: 700;
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
  .inp {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.tr {
  display: grid;
  grid-template-columns: 110px 70px 110px 1fr 1fr 90px minmax(140px, 1fr);
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
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}
.money {
  font-weight: 900;
}
.tag {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid rgba(99, 102, 241, 0.25);
  background: rgba(99, 102, 241, 0.12);
  font-weight: 800;
  font-size: 12px;
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
  margin: 8vh auto 16px;
  max-width: 720px;
  width: calc(100% - 32px);
  max-height: min(85vh, 920px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
  flex-shrink: 0;
}
.panel__scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
}
.panel__loading {
  padding: 8px 0 12px;
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
.k { opacity: 0.7; font-weight: 800; }
.v { font-weight: 800; }
.items { margin-top: 12px; }
.items__title { font-weight: 900; margin-bottom: 8px; }
.billing-msgs__empty {
  font-size: 13px;
  line-height: 1.45;
}
.billing-msgs__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.billing-msgs__row {
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.5);
}
@media (prefers-color-scheme: dark) {
  .billing-msgs__row {
    background: rgba(15, 23, 42, 0.35);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.billing-msgs__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  margin-bottom: 6px;
  font-size: 12px;
}
.billing-msgs__time {
  opacity: 0.85;
  font-weight: 700;
}
.billing-msgs__kind {
  font-size: 11px;
  padding: 2px 8px;
}
.tag--debit {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.28);
  color: #b91c1c;
}
.tag--credit {
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(34, 197, 94, 0.28);
  color: #15803d;
}
.billing-msgs__who {
  font-weight: 800;
  opacity: 0.9;
}
.billing-msgs__amt {
  font-weight: 900;
  font-size: 14px;
  margin-bottom: 4px;
}
.amt--debit {
  color: #b91c1c;
}
.amt--credit {
  color: #15803d;
}
.billing-msgs__remark {
  font-size: 13px;
  line-height: 1.45;
  opacity: 0.88;
}
.it { padding: 8px 0; border-top: 1px dashed rgba(15, 23, 42, 0.12); }
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
