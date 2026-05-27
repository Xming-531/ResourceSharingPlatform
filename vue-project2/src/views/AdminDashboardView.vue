<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { adminDashboardStats } from '@/api/admin'

const loading = ref(false)
const userCount = ref(0)
const equipmentCount = ref(0)
const completedOrderCount = ref(0)
const totalRevenue = ref('0.00')
const pendingEquipment = ref(0)
const pendingWorks = ref(0)
const pendingComments = ref(0)
/** @type {import('vue').Ref<{ date: string, count: number }[]>} */
const seriesRaw = ref([])

const cards = computed(() => [
  { key: 'users', label: '用户注册量', value: String(userCount.value), hint: '平台注册用户总数' },
  { key: 'goods', label: '商品数量', value: String(equipmentCount.value), hint: '资源/设备上架记录总数' },
  { key: 'orders', label: '订单成交数', value: String(completedOrderCount.value), hint: '状态为「已完成」的订单' },
  { key: 'revenue', label: '总成交金额', value: `¥ ${totalRevenue.value}`, hint: '已完成订单的订单总金额合计' },
])

const todoItems = computed(() => [
  {
    key: 'eq',
    label: '待审核商品',
    count: pendingEquipment.value,
    to: { name: 'adminResources', query: { status: '待审核' } },
  },
  {
    key: 'wk',
    label: '待审核作品',
    count: pendingWorks.value,
    to: { name: 'adminWorks', query: { status: '待审核' } },
  },
  {
    key: 'cm',
    label: '待审核评论',
    count: pendingComments.value,
    to: { name: 'adminWorkComments', query: { status: '待审核' } },
  },
])

const chartW = 720
const chartH = 260
const padL = 40
const padR = 16
const padT = 20
const padB = 36

const series = computed(() => seriesRaw.value || [])

function niceYMax(n) {
  const v = Math.max(0, Number(n) || 0)
  if (v <= 1) return 1
  const exp = Math.floor(Math.log10(v))
  const step = 10 ** Math.max(0, exp - 1)
  return Math.ceil(v / step) * step
}

const yMax = computed(() => niceYMax(Math.max(0, ...series.value.map((s) => s.count))))

const chartGeom = computed(() => {
  const pts = series.value
  const n = pts.length
  const innerW = chartW - padL - padR
  const innerH = chartH - padT - padB
  const maxY = yMax.value || 1
  if (n === 0) {
    return { points: '', areaPoints: '', dots: [], xLabels: [], yTicks: [], innerW, innerH, maxY }
  }
  const coords = pts.map((p, i) => {
    const x = n <= 1 ? padL + innerW / 2 : padL + (innerW * i) / (n - 1)
    const y = padT + innerH - (p.count / maxY) * innerH
    return { x, y, ...p }
  })
  const points = coords.map((c) => `${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ')
  const bottom = padT + innerH
  const areaPoints =
    coords.length > 0
      ? `${coords[0].x.toFixed(1)},${bottom} ${points} ${coords[coords.length - 1].x.toFixed(1)},${bottom}`
      : ''
  const xLabels = coords.map((c) => ({
    x: c.x,
    text: formatTickDate(c.date),
  }))
  const yTickCount = 5
  const yTicks = []
  for (let i = 0; i < yTickCount; i += 1) {
    const val = Math.round((maxY * i) / Math.max(1, yTickCount - 1))
    const y = padT + innerH - (val / maxY) * innerH
    yTicks.push({ y, val })
  }
  return { points, areaPoints, dots: coords, xLabels, yTicks, innerW, innerH, maxY }
})

function formatTickDate(iso) {
  if (!iso || typeof iso !== 'string') return ''
  const m = iso.slice(5, 7)
  const d = iso.slice(8, 10)
  return `${Number(m)}/${Number(d)}`
}

async function reload() {
  loading.value = true
  try {
    const res = await adminDashboardStats()
    const d = res?.data || {}
    userCount.value = Number(d.user_count) || 0
    equipmentCount.value = Number(d.equipment_count) || 0
    completedOrderCount.value = Number(d.completed_order_count) || 0
    totalRevenue.value = d.total_revenue != null ? String(d.total_revenue) : '0.00'
    const p = d.pending || {}
    pendingEquipment.value = Number(p.equipment) || 0
    pendingWorks.value = Number(p.works) || 0
    pendingComments.value = Number(p.comments) || 0
    const s = d.completed_orders_last_7_days
    seriesRaw.value = Array.isArray(s) ? s.map((x) => ({ date: String(x.date), count: Number(x.count) || 0 })) : []
  } catch (e) {
    alert(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(reload)
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">首页展示</div>
      <div class="sub">平台运营概览。</div>
      <button class="btn" type="button" :disabled="loading" @click="reload">
        {{ loading ? '刷新中…' : '刷新数据' }}
      </button>
    </div>

    <div class="grid">
      <article v-for="c in cards" :key="c.key" class="card">
        <div class="card__label">{{ c.label }}</div>
        <div class="card__value">{{ c.value }}</div>
        <div class="card__hint">{{ c.hint }}</div>
      </article>
    </div>

    <div class="lower">
      <div class="panel">
        <div class="panel__title">待办概览</div>
        <div class="panel__sub">点击进入对应管理页。</div>
        <ul class="todo">
          <li v-for="t in todoItems" :key="t.key" class="todo__row">
            <RouterLink class="todo__link" :to="t.to">
              <span class="todo__label">{{ t.label }}</span>
              <span class="todo__count" :class="{ zero: t.count === 0 }">{{ t.count }}</span>
              <span class="todo__arrow" aria-hidden="true">→</span>
            </RouterLink>
          </li>
        </ul>
      </div>

      <div class="panel panel--wide">
        <div class="panel__title">近 7 日订单成交趋势</div>
        <div class="panel__sub">按成交完成日统计「已完成」订单数量。</div>
        <div class="chart-wrap">
          <svg
            class="chart"
            :viewBox="`0 0 ${chartW} ${chartH}`"
            preserveAspectRatio="xMidYMid meet"
            role="img"
            aria-label="近七日订单成交折线图"
          >
            <defs>
              <linearGradient id="adminChartFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" class="chart-stop-a" />
                <stop offset="100%" class="chart-stop-b" />
              </linearGradient>
            </defs>

            <g class="chart__grid">
              <line
                v-for="(tk, idx) in chartGeom.yTicks"
                :key="'h' + idx"
                :x1="padL"
                :y1="tk.y"
                :x2="chartW - padR"
                :y2="tk.y"
              />
            </g>

            <g class="chart__yaxis">
              <text
                v-for="(tk, idx) in chartGeom.yTicks"
                :key="'y' + idx"
                x="4"
                :y="tk.y + 4"
                class="chart__axis-text"
              >
                {{ tk.val }}
              </text>
            </g>

            <template v-if="chartGeom.dots.length">
              <polygon class="chart__area" :points="chartGeom.areaPoints" />
              <polyline class="chart__line" fill="none" :points="chartGeom.points" />
              <circle
                v-for="(d, idx) in chartGeom.dots"
                :key="'d' + idx"
                class="chart__dot"
                :cx="d.x"
                :cy="d.y"
                r="4"
              />
            </template>
            <text v-else :x="chartW / 2" :y="chartH / 2" class="chart__empty" text-anchor="middle">暂无数据</text>

            <g class="chart__xaxis">
              <text
                v-for="(lb, idx) in chartGeom.xLabels"
                :key="'x' + idx"
                :x="lb.x"
                :y="chartH - 8"
                class="chart__axis-text chart__axis-text--x"
                text-anchor="middle"
              >
                {{ lb.text }}
              </text>
            </g>
          </svg>
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
  padding: 6px 6px 18px;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
}
.title {
  font-size: 18px;
  font-weight: 900;
  width: 100%;
}
.sub {
  font-size: 13px;
  opacity: 0.7;
  flex: 1;
  min-width: 200px;
  margin: 0;
}
.btn {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.4);
  color: inherit;
  border-radius: 12px;
  padding: 8px 14px;
  cursor: pointer;
  font-weight: 800;
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
@media (prefers-color-scheme: dark) {
  .btn {
    background: rgba(15, 23, 42, 0.35);
    border-color: rgba(148, 163, 184, 0.2);
  }
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}
.card {
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
@media (prefers-color-scheme: dark) {
  .card {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.card__label {
  font-size: 13px;
  font-weight: 800;
  opacity: 0.75;
}
.card__value {
  font-size: 26px;
  font-weight: 900;
  letter-spacing: -0.02em;
  word-break: break-all;
}
.card__hint {
  font-size: 12px;
  opacity: 0.55;
  line-height: 1.4;
}

.lower {
  margin-top: 20px;
  display: grid;
  grid-template-columns: minmax(240px, 320px) 1fr;
  gap: 14px;
  align-items: start;
}
@media (max-width: 900px) {
  .lower {
    grid-template-columns: 1fr;
  }
}

.panel {
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  padding: 18px 16px;
}
.panel--wide {
  min-width: 0;
}
@media (prefers-color-scheme: dark) {
  .panel {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.panel__title {
  font-size: 16px;
  font-weight: 900;
}
.panel__sub {
  font-size: 12px;
  opacity: 0.6;
  margin-top: 4px;
  margin-bottom: 14px;
  line-height: 1.4;
}

.todo {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.todo__link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(148, 163, 184, 0.1);
  text-decoration: none;
  color: inherit;
  font-weight: 800;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.todo__link:hover {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.35);
}
.todo__label {
  flex: 1;
}
.todo__count {
  font-variant-numeric: tabular-nums;
  font-size: 18px;
}
.todo__count.zero {
  opacity: 0.45;
}
.todo__arrow {
  opacity: 0.45;
}

.chart-wrap {
  width: 100%;
  max-width: 100%;
}
.chart {
  width: 100%;
  height: auto;
  display: block;
  overflow: visible;
}
.chart-stop-a {
  stop-color: rgba(99, 102, 241, 0.35);
}
.chart-stop-b {
  stop-color: rgba(99, 102, 241, 0.02);
}
@media (prefers-color-scheme: dark) {
  .chart-stop-a {
    stop-color: rgba(129, 140, 248, 0.4);
  }
  .chart-stop-b {
    stop-color: rgba(129, 140, 248, 0.03);
  }
}
.chart__grid line {
  stroke: rgba(15, 23, 42, 0.08);
  stroke-width: 1;
}
@media (prefers-color-scheme: dark) {
  .chart__grid line {
    stroke: rgba(148, 163, 184, 0.15);
  }
}
.chart__axis-text {
  font-size: 11px;
  fill: rgba(15, 23, 42, 0.55);
  font-weight: 700;
}
.chart__axis-text--x {
  font-size: 11px;
}
@media (prefers-color-scheme: dark) {
  .chart__axis-text {
    fill: rgba(226, 232, 240, 0.65);
  }
}
.chart__line {
  stroke: rgb(99, 102, 241);
  stroke-width: 2.5;
  stroke-linejoin: round;
  stroke-linecap: round;
}
.chart__area {
  fill: url(#adminChartFill);
  stroke: none;
}
.chart__dot {
  fill: rgb(99, 102, 241);
  stroke: rgba(255, 255, 255, 0.9);
  stroke-width: 2;
}
@media (prefers-color-scheme: dark) {
  .chart__line {
    stroke: rgb(165, 180, 252);
  }
  .chart__dot {
    fill: rgb(165, 180, 252);
    stroke: rgba(15, 23, 42, 0.95);
  }
}
.chart__empty {
  font-size: 14px;
  fill: rgba(15, 23, 42, 0.45);
  font-weight: 700;
}
@media (prefers-color-scheme: dark) {
  .chart__empty {
    fill: rgba(226, 232, 240, 0.45);
  }
}
</style>
