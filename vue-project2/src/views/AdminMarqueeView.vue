<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  adminCreateHomeMarquee,
  adminCreateHomeMarqueeJson,
  adminDeleteHomeMarquee,
  adminListHomeMarquee,
  adminPatchHomeMarquee,
  adminPatchHomeMarqueeForm,
} from '@/api/admin'

const list = ref([])
const loading = ref(false)

const editorOpen = ref(false)
const editingId = ref(null)
const formTitle = ref('')
const formSubtitle = ref('')
const formTrack = ref(1)
const formSort = ref(0)
const formEnabled = ref(true)
const formFile = ref(null)
const formImageUrl = ref('')
const saving = ref(false)

function resolveImg(u) {
  if (!u || typeof u !== 'string') return ''
  const t = u.trim()
  if (!t) return ''
  if (/^https?:\/\//i.test(t)) return t
  const base = import.meta.env.VITE_API_BASE_URL || ''
  return t.startsWith('/') ? `${base}${t}` : `${base}/${t}`
}

function trackLabel(t) {
  return Number(t) === 2 ? '慢轨' : '快轨'
}

async function reload() {
  loading.value = true
  try {
    const res = await adminListHomeMarquee()
    if (!res?.ok) throw new Error(res?.message || '加载失败')
    list.value = res.data || []
  } catch (e) {
    alert(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(reload)

function openCreate() {
  editingId.value = null
  formTitle.value = ''
  formSubtitle.value = ''
  formTrack.value = 1
  formSort.value = 0
  formEnabled.value = true
  formFile.value = null
  formImageUrl.value = ''
  editorOpen.value = true
}

function openEdit(row) {
  editingId.value = row.id
  formTitle.value = row.title || ''
  formSubtitle.value = row.subtitle || ''
  formTrack.value = Number(row.track) === 2 ? 2 : 1
  formSort.value = Number(row.sort_order) || 0
  formEnabled.value = !!row.enabled
  formFile.value = null
  formImageUrl.value = ''
  editorOpen.value = true
}

function closeEditor() {
  editorOpen.value = false
}

function onFileChange(ev) {
  const f = ev.target?.files?.[0]
  formFile.value = f || null
}

async function onSave() {
  const title = formTitle.value.trim()
  if (!title) {
    alert('请填写主标题')
    return
  }
  saving.value = true
  try {
    if (editingId.value == null) {
      if (formFile.value) {
        const fd = new FormData()
        fd.append('title', title)
        fd.append('subtitle', formSubtitle.value.trim())
        fd.append('track', String(formTrack.value))
        fd.append('sort_order', String(formSort.value))
        fd.append('enabled', formEnabled.value ? 'true' : 'false')
        fd.append('image', formFile.value)
        const res = await adminCreateHomeMarquee(fd)
        if (!res?.ok) throw new Error(res?.message || '创建失败')
      } else {
        const url = formImageUrl.value.trim()
        if (!url) {
          alert('请上传图片或填写图片地址')
          saving.value = false
          return
        }
        const res = await adminCreateHomeMarqueeJson({
          title,
          subtitle: formSubtitle.value.trim(),
          track: formTrack.value,
          sort_order: formSort.value,
          enabled: formEnabled.value,
          image_url: url,
        })
        if (!res?.ok) throw new Error(res?.message || '创建失败')
      }
    } else if (formFile.value) {
      const fd = new FormData()
      fd.append('title', title)
      fd.append('subtitle', formSubtitle.value.trim())
      fd.append('track', String(formTrack.value))
      fd.append('sort_order', String(formSort.value))
      fd.append('enabled', formEnabled.value ? 'true' : 'false')
      fd.append('image', formFile.value)
      const res = await adminPatchHomeMarqueeForm(editingId.value, fd)
      if (!res?.ok) throw new Error(res?.message || '保存失败')
    } else {
      const body = {
        title,
        subtitle: formSubtitle.value.trim(),
        track: formTrack.value,
        sort_order: formSort.value,
        enabled: formEnabled.value,
      }
      if (formImageUrl.value.trim()) {
        body.image_url = formImageUrl.value.trim()
      }
      const res = await adminPatchHomeMarquee(editingId.value, body)
      if (!res?.ok) throw new Error(res?.message || '保存失败')
    }
    closeEditor()
    await reload()
  } catch (e) {
    alert(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function onToggleEnabled(row) {
  try {
    const res = await adminPatchHomeMarquee(row.id, { enabled: !row.enabled })
    if (!res?.ok) throw new Error(res?.message || '更新失败')
    await reload()
  } catch (e) {
    alert(e?.message || '更新失败')
  }
}

async function onDelete(row) {
  if (!confirm(`确定删除「${row.title}」？`)) return
  try {
    const res = await adminDeleteHomeMarquee(row.id)
    if (!res?.ok) throw new Error(res?.message || '删除失败')
    await reload()
  } catch (e) {
    alert(e?.message || '删除失败')
  }
}

const editingRow = computed(() => list.value.find((x) => x.id === editingId.value))
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">首页精选展示</div>
      <div class="sub">管理用户首页「精选展示」图片与文案；关闭「显示」后前台不再展示该条。</div>
      <div class="head__actions">
        <button class="btn primary" type="button" :disabled="loading" @click="openCreate">新增条目</button>
        <button class="btn" type="button" :disabled="loading" @click="reload">刷新</button>
      </div>
    </div>

    <div v-if="loading" class="hint">加载中…</div>
    <div v-else-if="!list.length" class="hint">暂无条目，请点击「新增条目」。</div>

    <div v-else class="table">
      <div class="tr th">
        <div class="col-thumb">图</div>
        <div>主标题</div>
        <div>副标题</div>
        <div>轨道</div>
        <div>排序</div>
        <div>显示</div>
        <div class="col-ops">操作</div>
      </div>
      <div v-for="row in list" :key="row.id" class="tr">
        <div class="col-thumb">
          <img class="thumb" :src="resolveImg(row.image_url)" alt="" />
        </div>
        <div class="strong">{{ row.title }}</div>
        <div class="muted">{{ row.subtitle || '—' }}</div>
        <div>{{ trackLabel(row.track) }}</div>
        <div class="mono">{{ row.sort_order }}</div>
        <div>
          <button
            class="btn btn--sm"
            :class="row.enabled ? 'btn--on' : 'btn--off'"
            type="button"
            @click="onToggleEnabled(row)"
          >
            {{ row.enabled ? '显示中' : '已隐藏' }}
          </button>
        </div>
        <div class="col-ops">
          <button class="btn btn--sm" type="button" @click="openEdit(row)">编辑</button>
          <button class="btn btn--sm danger" type="button" @click="onDelete(row)">删除</button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="editorOpen" class="mask" @click.self="closeEditor">
        <div class="modal" role="dialog" aria-modal="true">
          <div class="modal__head">
            <div class="modal__title">{{ editingId == null ? '新增精选展示条目' : '编辑 #' + editingId }}</div>
            <button class="btn" type="button" @click="closeEditor">关闭</button>
          </div>
          <div class="modal__body">
            <label class="field">
              <span>主标题</span>
              <input v-model="formTitle" type="text" maxlength="120" placeholder="必填" />
            </label>
            <label class="field">
              <span>副标题</span>
              <input v-model="formSubtitle" type="text" maxlength="200" placeholder="可选" />
            </label>
            <label class="field">
              <span>轨道</span>
              <select v-model.number="formTrack">
                <option :value="1">快轨（上行，速度较快）</option>
                <option :value="2">慢轨（下行，速度较慢）</option>
              </select>
            </label>
            <label class="field">
              <span>排序</span>
              <input v-model.number="formSort" type="number" min="0" step="1" />
            </label>
            <label class="field field--row">
              <input v-model="formEnabled" type="checkbox" />
              <span>在用户首页显示</span>
            </label>
            <div v-if="editingRow" class="preview-wrap">
              <span class="preview-label">当前图</span>
              <img class="preview-img" :src="resolveImg(editingRow.image_url)" alt="" />
            </div>
            <label class="field">
              <span>上传图片</span>
              <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="onFileChange" />
            </label>
            <p v-if="editingId != null && editingRow" class="tip">可不换图；选择新文件或填写 URL 可替换。</p>
            <label class="field">
              <span>或填写图片 URL</span>
              <input v-model="formImageUrl" type="text" placeholder="http(s):// 或 /media/...（新增时若未选文件则必填）" />
            </label>
          </div>
          <div class="modal__foot">
            <button class="btn primary" type="button" :disabled="saving" @click="onSave">
              {{ saving ? '保存中…' : '保存' }}
            </button>
            <button class="btn" type="button" :disabled="saving" @click="closeEditor">取消</button>
          </div>
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
  margin-bottom: 16px;
}
.title {
  font-size: 18px;
  font-weight: 900;
}
.sub {
  font-size: 13px;
  opacity: 0.72;
  margin-top: 6px;
  max-width: 720px;
  line-height: 1.45;
}
.head__actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.hint {
  padding: 20px;
  opacity: 0.75;
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
}
.tr {
  display: grid;
  grid-template-columns: 100px 1fr 1fr 72px 56px 100px minmax(160px, 1fr);
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  font-size: 13px;
}
.tr.th {
  border-top: 0;
  font-weight: 900;
  background: rgba(148, 163, 184, 0.14);
}
.thumb {
  width: 88px;
  height: 50px;
  object-fit: cover;
  border-radius: 8px;
  display: block;
}
.strong {
  font-weight: 800;
}
.muted {
  opacity: 0.75;
  font-size: 12px;
}
.mono {
  font-family: ui-monospace, monospace;
}
.col-ops {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}
.btn {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.4);
  color: inherit;
  border-radius: 10px;
  padding: 8px 12px;
  cursor: pointer;
  font-weight: 800;
  font-size: 13px;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn.primary {
  border-color: rgba(99, 102, 241, 0.45);
  background: rgba(99, 102, 241, 0.18);
}
.btn--sm {
  padding: 6px 10px;
  font-size: 12px;
}
.btn--on {
  border-color: rgba(34, 197, 94, 0.45);
  background: rgba(34, 197, 94, 0.12);
}
.btn--off {
  opacity: 0.75;
}
.btn.danger {
  border-color: rgba(220, 38, 38, 0.4);
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}
.mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 8vh 16px;
  overflow: auto;
}
.modal {
  width: 100%;
  max-width: 480px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.98);
  padding: 14px;
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
  gap: 10px;
  margin-bottom: 12px;
}
.modal__title {
  font-weight: 900;
  font-size: 16px;
}
.modal__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  font-weight: 800;
}
.field--row {
  flex-direction: row;
  align-items: center;
  gap: 10px;
}
.field input[type='text'],
.field input[type='number'],
.field select {
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 10px;
  padding: 8px 10px;
  font-weight: 600;
}
.modal__foot {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.tip {
  font-size: 12px;
  opacity: 0.65;
  margin: 0;
}
.preview-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.preview-label {
  font-size: 12px;
  font-weight: 800;
  opacity: 0.7;
}
.preview-img {
  width: 100%;
  max-height: 140px;
  object-fit: contain;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.1);
}
@media (max-width: 900px) {
  .tr {
    grid-template-columns: 1fr;
  }
  .tr.th {
    display: none;
  }
  .col-ops {
    justify-content: flex-start;
  }
}
</style>
