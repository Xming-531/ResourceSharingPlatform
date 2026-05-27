<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  adminApproveWorkComment,
  adminDeleteWorkComment,
  adminFetchWorkComments,
  adminRejectWorkComment,
} from '@/api/works'
import { formatOrderDateTime } from '@/utils/datetime'
import defaultUserImg from '@/assets/default_user_img.png'

const route = useRoute()
const loading = ref(false)
const list = ref([])
const filterStatus = ref('')
const filterWorkId = ref('')

const viewingWork = ref(null)

function openWorkModal(c) {
  const w = c?.work
  if (!w) {
    alert('未找到关联作品数据，请刷新列表后重试')
    return
  }
  viewingWork.value = w
}

function closeWorkModal() {
  viewingWork.value = null
}

async function reload() {
  loading.value = true
  try {
    const res = await adminFetchWorkComments({
      status: filterStatus.value || undefined,
      work_id: filterWorkId.value.trim() || undefined,
    })
    list.value = res?.data || []
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

function avatarOf(c) {
  return c?.user?.avatar_url || defaultUserImg
}

function statusClass(s) {
  if (s === '待审核') return 'pending'
  if (s === '已通过') return 'approved'
  return 'rejected'
}

function workStatusClass(s) {
  if (s === '待审核') return 'pending'
  if (s === '已上架') return 'approved'
  if (s === '已下架' || s === '已驳回') return 'rejected'
  return 'pending'
}

async function onApprove(c) {
  if (c.status === '已驳回') {
    if (!confirm('确定重新通过该评论？通过后将对所有用户公开展示。')) return
  }
  try {
    await adminApproveWorkComment(c.comment_id)
    await reload()
  } catch (e) {
    alert(e?.message || '操作失败')
  }
}

async function onReject(c) {
  const msg =
    c.status === '已通过'
      ? '确定驳回该评论？驳回后将对其他用户隐藏（评论者仍可在照片展示看到自己评论为「已驳回」）。'
      : '确定驳回该待审核评论？'
  if (!confirm(msg)) return
  try {
    await adminRejectWorkComment(c.comment_id)
    await reload()
  } catch (e) {
    alert(e?.message || '操作失败')
  }
}

async function onDelete(c) {
  if (!confirm('确定删除该评论？')) return
  try {
    await adminDeleteWorkComment(c.comment_id)
    await reload()
  } catch (e) {
    alert(e?.message || '删除失败')
  }
}
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">作品评论管理</div>
      <div class="filters">
        <input v-model.trim="filterWorkId" class="inp" type="text" placeholder="作品 ID（可选）" />
        <select v-model="filterStatus" class="sel">
          <option value="">全部状态</option>
          <option value="待审核">待审核</option>
          <option value="已通过">已通过</option>
          <option value="已驳回">已驳回</option>
        </select>
        <button class="btn primary" type="button" :disabled="loading" @click="reload">查询</button>
      </div>
    </div>

    <div v-if="loading" class="hint">加载中…</div>
    <div v-else-if="!list.length" class="hint">暂无评论</div>
    <div v-else class="table">
      <div class="tr th">
        <div>ID</div>
        <div>作品</div>
        <div>用户</div>
        <div>内容</div>
        <div>状态</div>
        <div>时间</div>
        <div>操作</div>
      </div>
      <div v-for="c in list" :key="c.comment_id" class="tr">
        <div class="mono">#{{ c.comment_id }}</div>
        <div class="mono">#{{ c.work_id }}<span class="sub">{{ c.work_shoot_location }}</span></div>
        <div class="who">
          <img class="av" :src="avatarOf(c)" alt="" />
          <span>{{ c.user?.username || c.user_id }}</span>
        </div>
        <div class="content">{{ c.content }}</div>
        <div><span class="tag" :class="statusClass(c.status)">{{ c.status }}</span></div>
        <div class="mono small">{{ formatOrderDateTime(c.created_at) }}</div>
        <div class="ops">
          <button
            v-if="c.status === '待审核' || c.status === '已驳回'"
            class="btn ok"
            type="button"
            @click="onApprove(c)"
          >
            通过
          </button>
          <button
            v-if="c.status === '待审核' || c.status === '已通过'"
            class="btn no"
            type="button"
            @click="onReject(c)"
          >
            驳回
          </button>
          <button
            v-if="c.work"
            class="btn"
            type="button"
            @click="openWorkModal(c)"
          >
            查看作品
          </button>
          <button class="btn danger" type="button" @click="onDelete(c)">删除</button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="viewingWork" class="wmodal" role="dialog" aria-modal="true" aria-label="作品详情">
        <div class="wmodal__backdrop" @click="closeWorkModal"></div>
        <div class="wmodal__panel">
          <div class="wmodal__head">
            <div class="wmodal__title">作品 #{{ viewingWork.work_id }}</div>
            <button class="btn" type="button" @click="closeWorkModal">关闭</button>
          </div>
          <div class="wmodal__body">
            <div class="wmodal__imgwrap">
              <img v-if="viewingWork.image_url" class="wmodal__img" :src="viewingWork.image_url" alt="作品图片" />
              <div v-else class="wmodal__noimg">无图</div>
            </div>
            <div class="wkv">
              <div class="wkv__k">审核状态</div>
              <div class="wkv__v"><span class="tag" :class="workStatusClass(viewingWork.status)">{{ viewingWork.status }}</span></div>
              <div class="wkv__k">作者</div>
              <div class="wkv__v">{{ viewingWork.user?.username || viewingWork.user_id }}</div>
              <div class="wkv__k">拍摄地点</div>
              <div class="wkv__v">{{ viewingWork.shoot_location }}</div>
              <div class="wkv__k">相机</div>
              <div class="wkv__v">{{ viewingWork.camera_name }}</div>
              <div class="wkv__k">镜头</div>
              <div class="wkv__v">{{ viewingWork.lens_name }}</div>
              <div class="wkv__k">ISO</div>
              <div class="wkv__v">{{ viewingWork.iso }}</div>
              <div class="wkv__k">曝光</div>
              <div class="wkv__v">{{ viewingWork.shutter_speed }}</div>
              <div class="wkv__k">光圈</div>
              <div class="wkv__v">{{ viewingWork.aperture }}</div>
              <div class="wkv__k">创建时间</div>
              <div class="wkv__v mono">{{ formatOrderDateTime(viewingWork.created_at) }}</div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 16px;
}
.head {
  display: flex;
  flex-wrap: wrap;
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
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.inp,
.sel {
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 12px;
  padding: 10px 12px;
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
.btn.primary {
  border: none;
  background: linear-gradient(135deg, #6366f1, #22c55e);
  color: white;
}
.btn.ok {
  border-color: rgba(34, 197, 94, 0.35);
  background: rgba(34, 197, 94, 0.12);
}
.btn.no {
  border-color: rgba(234, 179, 8, 0.4);
  background: rgba(234, 179, 8, 0.12);
}
.btn.danger {
  border-color: rgba(220, 38, 38, 0.35);
  background: rgba(220, 38, 38, 0.08);
  color: #b91c1c;
}
.hint {
  opacity: 0.75;
  padding: 20px;
}
.table {
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 14px;
  overflow: hidden;
}
.tr {
  display: grid;
  grid-template-columns: 72px 120px 140px 1fr 90px 160px minmax(200px, auto);
  gap: 10px;
  padding: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  align-items: start;
  font-size: 13px;
}
.tr.th {
  border-top: none;
  background: rgba(148, 163, 184, 0.12);
  font-weight: 900;
}
.mono {
  font-family: ui-monospace, monospace;
}
.small {
  font-size: 12px;
}
.sub {
  display: block;
  font-size: 11px;
  opacity: 0.65;
  margin-top: 4px;
  word-break: break-all;
}
.who {
  display: flex;
  align-items: center;
  gap: 8px;
}
.av {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  object-fit: cover;
}
.content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.45;
}
.tag {
  display: inline-flex;
  padding: 4px 8px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 11px;
}
.tag.pending {
  background: rgba(234, 179, 8, 0.15);
}
.tag.approved {
  background: rgba(34, 197, 94, 0.15);
}
.tag.rejected {
  background: rgba(239, 68, 68, 0.12);
}
.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
@media (max-width: 1100px) {
  .tr {
    grid-template-columns: 1fr;
  }
  .tr.th {
    display: none;
  }
}

.wmodal {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: grid;
  place-items: center;
  padding: 20px;
}
.wmodal__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
}
.wmodal__panel {
  position: relative;
  width: min(560px, 100%);
  max-height: min(90vh, 720px);
  overflow: auto;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.18);
}
@media (prefers-color-scheme: dark) {
  .wmodal__panel {
    background: rgba(15, 23, 42, 0.96);
    border-color: rgba(148, 163, 184, 0.2);
  }
}
.wmodal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}
.wmodal__title {
  font-weight: 900;
  font-size: 16px;
}
.wmodal__body {
  padding: 14px;
}
.wmodal__imgwrap {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(2, 6, 23, 0.06);
  margin-bottom: 14px;
}
.wmodal__img {
  display: block;
  width: 100%;
  max-height: 320px;
  object-fit: contain;
}
.wmodal__noimg {
  padding: 40px;
  text-align: center;
  opacity: 0.6;
  font-weight: 700;
}
.wkv {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 8px 12px;
  font-size: 13px;
  align-items: baseline;
}
.wkv__k {
  font-weight: 800;
  opacity: 0.7;
}
.wkv__v {
  font-weight: 700;
  line-height: 1.4;
}
</style>
