<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { deleteWorkComment, fetchMyWorkComments } from '@/api/works'
import { formatOrderDateTime } from '@/utils/datetime'

const router = useRouter()

const loading = ref(false)
const list = ref([])
const deletingId = ref(null)

const sorted = computed(() => {
  const arr = [...list.value]
  arr.sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
  return arr
})

function previewText(content) {
  const t = String(content || '').trim()
  if (!t) return '（无内容）'
  return t.length > 80 ? `${t.slice(0, 80)}…` : t
}

function canOpenInSquare(row) {
  const w = row?.work
  return w && String(w.status || '') === '已上架'
}

function onViewWork(row) {
  const wid = row?.work?.work_id ?? row?.work_id
  if (!wid) return
  router.push({ name: 'square', query: { workId: String(wid) } })
}

async function load() {
  loading.value = true
  try {
    const res = await fetchMyWorkComments()
    if (!res?.ok) throw new Error(res?.message || '加载失败')
    list.value = res.data || []
  } catch (e) {
    alert(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function onDelete(row) {
  const workId = row?.work_id
  const commentId = row?.comment_id
  if (!workId || !commentId) return
  if (!confirm('确定删除这条评论？删除后不可恢复。')) return
  deletingId.value = commentId
  try {
    const res = await deleteWorkComment(workId, commentId)
    if (!res?.ok) throw new Error(res?.message || '删除失败')
    list.value = list.value.filter((x) => Number(x.comment_id) !== Number(commentId))
  } catch (e) {
    alert(e?.message || '删除失败')
  } finally {
    deletingId.value = null
  }
}

onMounted(load)
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">评论管理</div>
      <div class="sub">您在照片展示下发表的评论：可按发布时间查看、跳转到对应作品或删除。</div>
    </div>

    <div class="toolbar">
      <button class="btn primary" type="button" :disabled="loading" @click="load">刷新</button>
    </div>

    <div v-if="loading" class="hint">加载中…</div>
    <div v-else-if="!sorted.length" class="hint">暂无评论，请前往「照片展示」参与讨论。</div>

    <div v-else class="table-wrap">
      <table class="tbl" aria-label="我的评论列表">
        <thead>
          <tr>
            <th scope="col">发布时间</th>
            <th scope="col">作品</th>
            <th scope="col">评论内容</th>
            <th scope="col">状态</th>
            <th scope="col" class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in sorted" :key="row.comment_id">
            <td class="mono time">{{ formatOrderDateTime(row.created_at) }}</td>
            <td class="workcell">
              <div v-if="row.work" class="workcell-inner">
                <img class="thumb" :src="row.work.image_url" alt="" loading="lazy" />
                <div class="workmeta">
                  <div class="clamp" :title="row.work.shoot_location">{{ row.work.shoot_location || '（未填地点）' }}</div>
                  <div class="subline mono">#{{ row.work.work_id }} · {{ row.work.status }}</div>
                </div>
              </div>
              <span v-else class="muted">作品已删除</span>
            </td>
            <td class="content">{{ previewText(row.content) }}</td>
            <td><span class="pill">{{ row.status }}</span></td>
            <td class="col-actions">
              <div class="ops">
                <button
                  class="btn sm"
                  type="button"
                  :disabled="!canOpenInSquare(row)"
                  :title="!canOpenInSquare(row) ? '仅「已上架」作品可从照片展示打开' : '在照片展示中打开该作品评论'"
                  @click="onViewWork(row)"
                >
                  查看作品
                </button>
                <button
                  class="btn sm danger"
                  type="button"
                  :disabled="deletingId === row.comment_id"
                  @click="onDelete(row)"
                >
                  {{ deletingId === row.comment_id ? '删除中…' : '删除' }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.page {
  padding: 18px 16px 40px;
  max-width: 1100px;
  margin: 0 auto;
}
.head {
  margin-bottom: 14px;
}
.title {
  font-size: 22px;
  font-weight: 900;
  letter-spacing: 0.02em;
}
.sub {
  margin-top: 6px;
  font-size: 13px;
  opacity: 0.78;
  line-height: 1.5;
}
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.hint {
  padding: 28px 12px;
  text-align: center;
  opacity: 0.75;
  font-weight: 700;
}
.table-wrap {
  overflow: auto;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.55);
}
@media (prefers-color-scheme: dark) {
  .table-wrap {
    background: rgba(15, 23, 42, 0.45);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.tbl th,
.tbl td {
  padding: 12px 10px;
  text-align: left;
  vertical-align: middle;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}
.tbl th {
  font-weight: 900;
  font-size: 12px;
  text-transform: none;
  letter-spacing: 0.02em;
  background: rgba(2, 6, 23, 0.04);
}
.col-actions {
  width: 200px;
  white-space: nowrap;
  vertical-align: middle;
}
.time {
  white-space: nowrap;
  min-width: 158px;
}
.workcell {
  min-width: 200px;
  vertical-align: middle;
}
.workcell-inner {
  display: flex;
  align-items: center;
  gap: 10px;
}
.thumb {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 10px;
  flex-shrink: 0;
  background: rgba(2, 6, 23, 0.06);
}
.workmeta {
  min-width: 0;
}
.clamp {
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 220px;
}
.subline {
  margin-top: 4px;
  font-size: 11px;
  opacity: 0.72;
}
.content {
  max-width: 320px;
  line-height: 1.45;
  color: inherit;
  opacity: 0.92;
}
.pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 12px;
  background: rgba(59, 130, 246, 0.12);
}
.ops {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.btn {
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.85);
  padding: 8px 12px;
  font-weight: 800;
  cursor: pointer;
  color: inherit;
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn.primary {
  border-color: rgba(59, 130, 246, 0.35);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.95), rgba(99, 102, 241, 0.92));
  color: #fff;
}
.btn.sm {
  padding: 6px 10px;
  font-size: 12px;
}
.btn.danger {
  border-color: rgba(239, 68, 68, 0.35);
  color: #b91c1c;
  background: rgba(254, 226, 226, 0.55);
}
.muted {
  opacity: 0.65;
  font-weight: 700;
}
.mono {
  font-variant-numeric: tabular-nums;
}
@media (prefers-color-scheme: dark) {
  .btn {
    background: rgba(2, 6, 23, 0.55);
    border-color: rgba(148, 163, 184, 0.2);
  }
  .btn.danger {
    color: #fecaca;
    background: rgba(127, 29, 29, 0.35);
  }
}
</style>
