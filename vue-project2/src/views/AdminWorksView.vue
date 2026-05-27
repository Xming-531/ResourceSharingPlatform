<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  adminApproveWork,
  adminDeleteWork,
  adminFetchWorks,
  adminOffShelfWork,
  adminOnShelfWork,
  adminRejectWork,
} from '@/api/works'
import defaultUserImg from '@/assets/default_user_img.png'

const route = useRoute()

const loading = ref(false)
const works = ref([])
const filterStatus = ref('')
const viewing = ref(null)

const filtered = computed(() => {
  const s = (filterStatus.value || '').trim()
  if (!s) return works.value
  return works.value.filter((w) => String(w.status || '') === s)
})

function avatarOf(w) {
  return w?.user?.avatar_url || defaultUserImg
}

function usernameOf(w) {
  return w?.user?.username || `用户${w?.user_id ?? ''}`
}

async function reload() {
  loading.value = true
  try {
    const res = await adminFetchWorks({})
    works.value = res?.data || []
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

function onView(w) {
  viewing.value = w
}
function closeView() {
  viewing.value = null
}

async function onApprove(w) {
  if (w.status === '已驳回') {
    if (!confirm('确定将该驳回作品重新审核通过并上架展示？')) return
  }
  try {
    await adminApproveWork(w.work_id)
    await reload()
    if (viewing.value?.work_id === w.work_id) {
      const hit = works.value.find((x) => x.work_id === w.work_id)
      if (hit) viewing.value = hit
      else closeView()
    }
  } catch (e) {
    alert(e?.message || '审核失败')
  }
}

async function onReject(w) {
  if (!confirm('确定驳回该作品？驳回后不会在照片展示中展示，作者可在「我的作品」中看到状态。')) return
  try {
    await adminRejectWork(w.work_id)
    await reload()
    if (viewing.value?.work_id === w.work_id) {
      const hit = works.value.find((x) => x.work_id === w.work_id)
      if (hit) viewing.value = hit
      else closeView()
    }
  } catch (e) {
    alert(e?.message || '驳回失败')
  }
}

async function onOff(w) {
  try {
    await adminOffShelfWork(w.work_id)
    await reload()
    if (viewing.value?.work_id === w.work_id) {
      const hit = works.value.find((x) => x.work_id === w.work_id)
      if (hit) viewing.value = hit
      else closeView()
    }
  } catch (e) {
    alert(e?.message || '下架失败')
  }
}

async function onOnShelf(w) {
  if (!confirm('确定将该已下架作品重新上架到照片展示？')) return
  try {
    await adminOnShelfWork(w.work_id)
    await reload()
    if (viewing.value?.work_id === w.work_id) {
      const hit = works.value.find((x) => x.work_id === w.work_id)
      if (hit) viewing.value = hit
      else closeView()
    }
  } catch (e) {
    alert(e?.message || '上架失败')
  }
}

function workStatusNorm(w) {
  return String(w?.status ?? '').trim()
}

function canAdminDeleteWork(w) {
  const s = workStatusNorm(w)
  return s === '待审核' || s === '已下架' || s === '已驳回'
}

async function onDelete(w) {
  if (!canAdminDeleteWork(w)) {
    alert('仅「待审核」「已下架」或「已驳回」的作品可删除；已上架请先点「下架」。')
    return
  }
  if (!confirm(`确定删除作品 #${w.work_id}？删除后不可恢复。`)) return
  try {
    const res = await adminDeleteWork(w.work_id)
    if (!res?.ok) throw new Error(res?.message || '删除失败')
    if (viewing.value?.work_id === w.work_id) closeView()
    await reload()
  } catch (e) {
    alert(e?.message || '删除失败')
  }
}
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">作品审核</div>
      <div class="filters">
        <select v-model="filterStatus" class="sel">
          <option value="">全部</option>
          <option value="待审核">待审核</option>
          <option value="已上架">已上架</option>
          <option value="已下架">已下架</option>
          <option value="已驳回">已驳回</option>
        </select>
        <button class="btn" type="button" @click="reload">刷新</button>
      </div>
    </div>

    <div v-if="loading" class="hint">加载中…</div>
    <div v-else-if="filtered.length === 0" class="hint">暂无数据</div>

    <div v-else class="table">
      <div class="tr th">
        <div>ID</div>
        <div>作者</div>
        <div>地点</div>
        <div>状态</div>
        <div>操作</div>
      </div>
      <div v-for="w in filtered" :key="w.work_id" class="tr">
        <div>#{{ w.work_id }}</div>
        <div class="who">
          <img class="avatar" :src="avatarOf(w)" alt="avatar" />
          <span>{{ usernameOf(w) }}</span>
        </div>
        <div>{{ w.shoot_location }}</div>
        <div>
          <span class="tag" :class="`s_${w.status}`">{{ w.status }}</span>
        </div>
        <div class="ops">
          <button class="btn" type="button" @click="onView(w)">查看</button>
          <button v-if="w.status === '待审核' || w.status === '已驳回'" class="btn primary" type="button" @click="onApprove(w)">
            通过
          </button>
          <button v-if="w.status === '待审核'" class="btn warn" type="button" @click="onReject(w)">驳回</button>
          <button v-if="w.status === '已上架'" class="btn danger" type="button" @click="onOff(w)">下架</button>
          <button v-if="w.status === '已下架'" class="btn primary" type="button" @click="onOnShelf(w)">上架</button>
          <button
            v-if="canAdminDeleteWork(w)"
            class="btn danger-outline"
            type="button"
            title="待审核、已下架或已驳回的作品可删除"
            @click="onDelete(w)"
          >
            删除
          </button>
        </div>
      </div>
    </div>

    <div v-if="viewing" class="mask" @click.self="closeView">
      <div class="modal">
        <div class="modal__head">
          <div class="modal__title">作品详情 #{{ viewing.work_id }}</div>
          <button class="x" type="button" @click="closeView">×</button>
        </div>
        <div class="body">
          <div class="img"><img :src="viewing.image_url" alt="work" /></div>
          <div class="meta">
            <div class="line"><span class="k">作者</span><span class="v">{{ usernameOf(viewing) }}</span></div>
            <div class="line"><span class="k">地点</span><span class="v">{{ viewing.shoot_location }}</span></div>
            <div class="line"><span class="k">相机</span><span class="v">{{ viewing.camera_name }}</span></div>
            <div class="line"><span class="k">镜头</span><span class="v">{{ viewing.lens_name }}</span></div>
            <div class="line"><span class="k">ISO</span><span class="v">{{ viewing.iso }}</span></div>
            <div class="line"><span class="k">曝光</span><span class="v">{{ viewing.shutter_speed }}</span></div>
            <div class="line"><span class="k">光圈</span><span class="v">{{ viewing.aperture }}</span></div>
            <div class="line"><span class="k">状态</span><span class="v">{{ viewing.status }}</span></div>
          </div>
        </div>
        <div class="foot">
          <button class="btn" type="button" @click="closeView">关闭</button>
          <button
            v-if="viewing.status === '待审核' || viewing.status === '已驳回'"
            class="btn primary"
            type="button"
            @click="onApprove(viewing)"
          >
            通过
          </button>
          <button v-if="viewing.status === '待审核'" class="btn warn" type="button" @click="onReject(viewing)">驳回</button>
          <button v-if="viewing.status === '已上架'" class="btn danger" type="button" @click="onOff(viewing)">下架</button>
          <button v-if="viewing.status === '已下架'" class="btn primary" type="button" @click="onOnShelf(viewing)">上架</button>
          <button
            v-if="canAdminDeleteWork(viewing)"
            class="btn danger-outline"
            type="button"
            @click="onDelete(viewing)"
          >
            删除
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.page {
  max-width: 1240px;
  margin: 0 auto;
  padding: 16px;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.title {
  font-weight: 900;
  font-size: 18px;
}
.filters {
  display: flex;
  align-items: center;
  gap: 10px;
}
.sel {
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.6);
}
.btn {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.5);
  color: inherit;
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 800;
}
.btn.primary {
  border: none;
  background: linear-gradient(135deg, #6366f1, #22c55e);
  color: white;
}
.btn.danger {
  border: none;
  background: linear-gradient(135deg, #ef4444, #fb7185);
  color: white;
}
.btn.warn {
  border: 1px solid rgba(234, 179, 8, 0.45);
  background: rgba(234, 179, 8, 0.15);
  color: #a16207;
}
@media (prefers-color-scheme: dark) {
  .btn.warn {
    color: #fcd34d;
  }
}
.tag.s_已驳回 {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.28);
}
.btn.danger-outline {
  border: 1px solid rgba(220, 38, 38, 0.45);
  background: rgba(220, 38, 38, 0.08);
  color: #b91c1c;
}
@media (prefers-color-scheme: dark) {
  .btn.danger-outline {
    color: #fecaca;
  }
}
.hint {
  opacity: 0.75;
  padding: 24px 8px;
}
.table {
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 14px;
  overflow: hidden;
}
.tr {
  display: grid;
  grid-template-columns: 110px 220px 1fr 140px 260px;
  gap: 10px;
  padding: 12px 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  align-items: center;
}
.tr.th {
  border-top: none;
  background: rgba(148, 163, 184, 0.12);
  font-weight: 900;
}
.who {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.avatar {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  object-fit: cover;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(148, 163, 184, 0.14);
}
.tag {
  display: inline-flex;
  padding: 6px 10px;
  border-radius: 999px;
  font-weight: 900;
  font-size: 12px;
  background: rgba(148, 163, 184, 0.12);
}
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mask {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.55);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 50;
}
.modal {
  width: min(920px, 100%);
  border-radius: 16px;
  background: white;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.16);
}
.modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}
.modal__title {
  font-weight: 900;
}
.x {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
}
.body {
  padding: 14px;
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 12px;
}
@media (max-width: 820px) {
  .body {
    grid-template-columns: 1fr;
  }
}
.img {
  border-radius: 14px;
  overflow: hidden;
  background: rgba(148, 163, 184, 0.12);
  aspect-ratio: 4 / 3;
}
.img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.meta {
  display: grid;
  gap: 8px;
  font-size: 13px;
}
.line {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.k {
  opacity: 0.7;
}
.v {
  font-weight: 900;
}
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 14px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}
</style>

