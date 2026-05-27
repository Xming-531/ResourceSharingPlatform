<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  deleteMyWork,
  fetchMyWorks,
  offShelfMyWork,
  reapplyMyWork,
  updateMyWork,
  withdrawMyWork,
} from '@/api/works'
import { formatOrderDateTime } from '@/utils/datetime'

const list = ref([])
const loading = ref(false)
const filterStatus = ref('')

const viewWork = ref(null)
const editWork = ref(null)
const editBusy = ref(false)
const editForm = ref({
  camera_name: '',
  lens_name: '',
  iso: '',
  shutter_speed: '',
  aperture: '',
  shoot_location: '',
})
const editImage = ref(null)

const filtered = computed(() => {
  const s = (filterStatus.value || '').trim()
  if (!s) return list.value
  return list.value.filter((w) => String(w.status || '') === s)
})

function canEdit(w) {
  return w.status === '待审核' || w.status === '已驳回' || w.status === '已下架'
}

function canDelete(w) {
  return canEdit(w)
}

function canReapply(w) {
  return w.status === '已驳回' || w.status === '已下架' || w.status === '已撤回'
}

function canOffShelf(w) {
  return w.status === '已上架'
}

function canWithdraw(w) {
  return w.status === '待审核'
}

function statusClass(s) {
  if (s === '待审核') return 'pending'
  if (s === '已上架') return 'on'
  if (s === '已驳回') return 'reject'
  if (s === '已下架') return 'off'
  if (s === '已撤回') return 'off'
  return ''
}

async function reload() {
  loading.value = true
  try {
    const res = await fetchMyWorks()
    if (!res?.ok) throw new Error(res?.message || '加载失败')
    list.value = res.data || []
  } catch (e) {
    alert(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(reload)

function openView(w) {
  viewWork.value = w
}

function closeView() {
  viewWork.value = null
}

function openEdit(w) {
  if (!canEdit(w)) {
    alert('当前状态不可编辑；已上架请先在列表中「下架」。')
    return
  }
  editWork.value = w
  editForm.value = {
    camera_name: w.camera_name || '',
    lens_name: w.lens_name || '',
    iso: w.iso || '',
    shutter_speed: w.shutter_speed || '',
    aperture: w.aperture || '',
    shoot_location: w.shoot_location || '',
  }
  editImage.value = null
}

function closeEdit() {
  editWork.value = null
  editImage.value = null
}

function onEditPickFile(e) {
  const f = e?.target?.files?.[0] || null
  editImage.value = f
}

async function submitEdit() {
  const w = editWork.value
  if (!w) return
  const f = editForm.value
  const required = ['camera_name', 'lens_name', 'iso', 'shutter_speed', 'aperture', 'shoot_location']
  for (const k of required) {
    if (!String(f[k] || '').trim()) {
      alert('请完整填写拍摄参数与地点')
      return
    }
  }
  editBusy.value = true
  try {
    const fd = new FormData()
    fd.append('camera_name', f.camera_name.trim())
    fd.append('lens_name', f.lens_name.trim())
    fd.append('iso', f.iso.trim())
    fd.append('shutter_speed', f.shutter_speed.trim())
    fd.append('aperture', f.aperture.trim())
    fd.append('shoot_location', f.shoot_location.trim())
    if (editImage.value) fd.append('image', editImage.value)
    const res = await updateMyWork(w.work_id, fd)
    if (!res?.ok) throw new Error(res?.message || '保存失败')
    closeEdit()
    await reload()
  } catch (e) {
    alert(e?.message || '保存失败')
  } finally {
    editBusy.value = false
  }
}

async function onReapply(w) {
  if (!canReapply(w)) return
  if (!confirm('确定重新提交审核？提交后状态将变为「待审核」。')) return
  try {
    const res = await reapplyMyWork(w.work_id)
    if (!res?.ok) throw new Error(res?.message || '操作失败')
    await reload()
  } catch (e) {
    alert(e?.message || '操作失败')
  }
}

async function onWithdraw(w) {
  if (!canWithdraw(w)) return
  if (!confirm('确定撤回申请？撤回后状态将变为「已撤回」。')) return
  try {
    const res = await withdrawMyWork(w.work_id)
    if (!res?.ok) throw new Error(res?.message || '操作失败')
    await reload()
  } catch (e) {
    alert(e?.message || '操作失败')
  }
}

async function onOffShelf(w) {
  if (!canOffShelf(w)) return
  if (!confirm('确定下架？下架后作品将从照片展示中移除，您可继续修改或删除。')) return
  try {
    const res = await offShelfMyWork(w.work_id)
    if (!res?.ok) throw new Error(res?.message || '下架失败')
    await reload()
  } catch (e) {
    alert(e?.message || '下架失败')
  }
}

async function onDelete(w) {
  if (!canDelete(w)) return
  if (!confirm(`确定删除作品 #${w.work_id}？删除后不可恢复。`)) return
  try {
    const res = await deleteMyWork(w.work_id)
    if (!res?.ok) throw new Error(res?.message || '删除失败')
    if (viewWork.value?.work_id === w.work_id) closeView()
    if (editWork.value?.work_id === w.work_id) closeEdit()
    await reload()
  } catch (e) {
    alert(e?.message || '删除失败')
  }
}
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">我的作品</div>
      <div class="sub">
        管理您在照片展示发布的图片：查看、修改拍摄参数、删除；被驳回或已下架后可重新申请审核。已上架作品需先下架再编辑或删除。
      </div>
    </div>

    <div class="toolbar">
      <label class="lbl" for="mw-filter">状态</label>
      <select id="mw-filter" v-model="filterStatus" class="sel">
        <option value="">全部</option>
        <option value="待审核">待审核</option>
        <option value="已上架">已上架</option>
        <option value="已驳回">已驳回</option>
        <option value="已下架">已下架</option>
        <option value="已撤回">已撤回</option>
      </select>
      <button class="btn primary" type="button" :disabled="loading" @click="reload">刷新</button>
    </div>

    <div v-if="loading" class="hint">加载中…</div>
    <div v-else-if="!filtered.length" class="hint">暂无作品，请前往「照片展示」发布。</div>
    <div v-else class="grid">
      <article v-for="w in filtered" :key="w.work_id" class="card">
        <div class="thumb">
          <img v-if="w.image_url" class="thumb__img" :src="w.image_url" alt="" loading="lazy" />
          <div v-else class="ph">无图</div>
        </div>
        <div class="body">
          <div class="row top">
            <span class="tag" :class="statusClass(w.status)">{{ w.status }}</span>
            <span class="mono">#{{ w.work_id }}</span>
          </div>
          <div class="loc clamp-1" :title="w.shoot_location">{{ w.shoot_location }}</div>
          <div class="meta clamp-2" :title="`${w.camera_name || ''} · ${w.lens_name || ''}`">
            {{ w.camera_name }} · {{ w.lens_name }}
          </div>
          <div class="time">{{ formatOrderDateTime(w.created_at) }}</div>
          <div class="ops">
            <button class="btn" type="button" @click="openView(w)">查看</button>
            <button class="btn" type="button" :disabled="!canEdit(w)" :title="!canEdit(w) ? '已上架请先下架' : ''" @click="openEdit(w)">
              修改参数
            </button>
            <button v-if="canWithdraw(w)" class="btn" type="button" @click="onWithdraw(w)">撤回申请</button>
            <button
              v-if="canReapply(w)"
              class="btn accent"
              type="button"
              @click="onReapply(w)"
            >
              重新申请
            </button>
            <button v-if="canOffShelf(w)" class="btn warn" type="button" @click="onOffShelf(w)">下架</button>
            <button class="btn danger" type="button" :disabled="!canDelete(w)" @click="onDelete(w)">删除</button>
          </div>
        </div>
      </article>
    </div>

    <Teleport to="body">
      <div v-if="viewWork" class="mask" role="dialog" aria-modal="true" aria-label="作品详情">
        <div class="backdrop" @click="closeView"></div>
        <div class="modal">
          <div class="modal__head">
            <div class="modal__title">作品 #{{ viewWork.work_id }}</div>
            <button class="x" type="button" @click="closeView">×</button>
          </div>
          <div class="modal__body">
            <div class="bigimg">
              <img v-if="viewWork.image_url" :src="viewWork.image_url" alt="作品" />
            </div>
            <div class="kv">
              <div class="k">状态</div>
              <div class="v"><span class="tag" :class="statusClass(viewWork.status)">{{ viewWork.status }}</span></div>
              <div class="k">地点</div>
              <div class="v">{{ viewWork.shoot_location }}</div>
              <div class="k">相机</div>
              <div class="v">{{ viewWork.camera_name }}</div>
              <div class="k">镜头</div>
              <div class="v">{{ viewWork.lens_name }}</div>
              <div class="k">ISO</div>
              <div class="v">{{ viewWork.iso }}</div>
              <div class="k">曝光</div>
              <div class="v">{{ viewWork.shutter_speed }}</div>
              <div class="k">光圈</div>
              <div class="v">{{ viewWork.aperture }}</div>
              <div class="k">创建</div>
              <div class="v mono">{{ formatOrderDateTime(viewWork.created_at) }}</div>
            </div>
          </div>
          <div class="modal__foot">
            <button class="btn" type="button" @click="closeView">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="editWork" class="mask" role="dialog" aria-modal="true">
        <div class="backdrop" @click="closeEdit"></div>
        <div class="modal modal--narrow">
          <div class="modal__head">
            <div class="modal__title">修改参数 #{{ editWork.work_id }}</div>
            <button class="x" type="button" @click="closeEdit">×</button>
          </div>
          <form class="form" @submit.prevent="submitEdit">
            <p class="tip">保存后，若当前为「已驳回」或「已下架」，将自动变为「待审核」重新排队。</p>
            <label class="field">
              <span>更换图片（可选）</span>
              <input type="file" accept="image/*" @change="onEditPickFile" />
            </label>
            <label class="field">
              <span>相机</span>
              <input v-model.trim="editForm.camera_name" type="text" required />
            </label>
            <label class="field">
              <span>镜头</span>
              <input v-model.trim="editForm.lens_name" type="text" required />
            </label>
            <label class="field">
              <span>ISO</span>
              <input v-model.trim="editForm.iso" type="text" required />
            </label>
            <label class="field">
              <span>曝光</span>
              <input v-model.trim="editForm.shutter_speed" type="text" required />
            </label>
            <label class="field">
              <span>光圈</span>
              <input v-model.trim="editForm.aperture" type="text" required />
            </label>
            <label class="field">
              <span>拍摄地点</span>
              <input v-model.trim="editForm.shoot_location" type="text" required />
            </label>
            <div class="modal__foot">
              <button class="btn" type="button" :disabled="editBusy" @click="closeEdit">取消</button>
              <button class="btn primary" type="submit" :disabled="editBusy">{{ editBusy ? '保存中…' : '保存' }}</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px;
}
.head {
  margin-bottom: 14px;
}
.title {
  font-weight: 900;
  font-size: 18px;
}
.sub {
  font-size: 13px;
  opacity: 0.72;
  margin-top: 6px;
  line-height: 1.5;
  max-width: 52rem;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.lbl {
  font-size: 13px;
  font-weight: 800;
  opacity: 0.8;
}
.sel {
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 12px;
  padding: 8px 12px;
  min-width: 140px;
}
.btn {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.5);
  border-radius: 12px;
  padding: 8px 12px;
  cursor: pointer;
  font-weight: 800;
  font-size: 13px;
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn.primary {
  border: none;
  background: linear-gradient(135deg, #6366f1, #22c55e);
  color: #fff;
}
.btn.accent {
  border-color: rgba(99, 102, 241, 0.35);
  background: rgba(99, 102, 241, 0.12);
}
.btn.warn {
  border-color: rgba(234, 179, 8, 0.45);
  background: rgba(234, 179, 8, 0.12);
  color: #a16207;
}
.btn.danger {
  border-color: rgba(220, 38, 38, 0.35);
  background: rgba(220, 38, 38, 0.08);
  color: #b91c1c;
}
.hint {
  padding: 28px 8px;
  opacity: 0.7;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.card {
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
}
@media (prefers-color-scheme: dark) {
  .card {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.thumb {
  position: relative;
  aspect-ratio: 4 / 3;
  background: rgba(2, 6, 23, 0.06);
  overflow: hidden;
}
.thumb__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  position: absolute;
  inset: 0;
}
.ph {
  height: 100%;
  display: grid;
  place-items: center;
  opacity: 0.5;
  font-weight: 800;
}
.body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}
.row.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.tag {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 900;
}
.tag.pending {
  background: rgba(234, 179, 8, 0.15);
}
.tag.on {
  background: rgba(34, 197, 94, 0.15);
}
.tag.reject {
  background: rgba(239, 68, 68, 0.12);
}
.tag.off {
  background: rgba(148, 163, 184, 0.2);
}
.mono {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  opacity: 0.75;
}
.loc {
  font-weight: 800;
  font-size: 14px;
}
.meta {
  font-size: 12px;
  opacity: 0.75;
}
.time {
  font-size: 12px;
  opacity: 0.6;
}
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  margin-top: auto;
}

.clamp-1,
.clamp-2 {
  min-width: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
}
.clamp-1 {
  -webkit-line-clamp: 1;
  line-clamp: 1;
}
.clamp-2 {
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.mask {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 16px;
}
.backdrop {
  position: absolute;
  inset: 0;
  background: rgba(2, 6, 23, 0.55);
}
.modal {
  position: relative;
  width: min(720px, 100%);
  max-height: 90vh;
  overflow: auto;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(15, 23, 42, 0.12);
}
.modal--narrow {
  width: min(440px, 100%);
}
@media (prefers-color-scheme: dark) {
  .modal {
    background: rgba(15, 23, 42, 0.96);
    border-color: rgba(148, 163, 184, 0.2);
  }
}
.modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}
.modal__title {
  font-weight: 900;
}
.x {
  border: none;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
  line-height: 1;
}
.modal__body {
  padding: 14px;
}
.bigimg {
  border-radius: 12px;
  overflow: hidden;
  background: rgba(2, 6, 23, 0.06);
  margin-bottom: 12px;
}
.bigimg img {
  width: 100%;
  max-height: 360px;
  object-fit: contain;
  display: block;
}
.kv {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 8px 10px;
  font-size: 13px;
}
.k {
  opacity: 0.7;
  font-weight: 800;
}
.v {
  font-weight: 700;
}
.modal__foot {
  padding: 12px 14px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.form {
  padding: 14px;
  display: grid;
  gap: 12px;
}
.tip {
  font-size: 12px;
  opacity: 0.75;
  margin: 0;
  line-height: 1.45;
}
.field {
  display: grid;
  gap: 6px;
  font-size: 12px;
  font-weight: 800;
}
.field input[type='text'],
.field input[type='file'] {
  font-weight: 600;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.8);
  color: inherit;
}
@media (prefers-color-scheme: dark) {
  .field input[type='text'] {
    background: rgba(2, 6, 23, 0.4);
    border-color: rgba(148, 163, 184, 0.2);
  }
}
</style>
