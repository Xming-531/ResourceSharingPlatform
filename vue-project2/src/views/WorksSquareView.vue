<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { createWork, deleteWorkComment, fetchWorkComments, fetchWorksPublic, postWorkComment } from '@/api/works'
import { formatOrderDateTime } from '@/utils/datetime'
import { goLogin } from '@/utils/authNavigate'
import { getSession, isAdmin, isLoggedIn } from '@/utils/session'
import defaultUserImg from '@/assets/default_user_img.png'
import ImageLightbox from '@/components/ImageLightbox.vue'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const works = ref([])

const showCreate = ref(false)
const creating = ref(false)

const commentModalWork = ref(null)
const comments = ref([])
const commentLoading = ref(false)
const newComment = ref('')
const commentSubmitting = ref(false)

const imageLightboxOpen = ref(false)
const imageLightboxSrc = ref('')
const imageLightboxAlt = ref('')

const form = ref({
  image: null,
  camera_name: '',
  lens_name: '',
  iso: '',
  shutter_speed: '',
  aperture: '',
  shoot_location: '',
})

const me = computed(() => getSession()?.user || null)
const currentUserId = computed(() => Number(me.value?.id))
const isAdminUser = computed(() => isAdmin())

function userAvatar(w) {
  return w?.user?.avatar_url || defaultUserImg
}

function userName(w) {
  return w?.user?.username || `用户${w?.user_id ?? ''}`
}

async function reload() {
  loading.value = true
  try {
    const res = await fetchWorksPublic()
    works.value = res?.data || []
  } catch (e) {
    alert(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function tryOpenWorkFromQuery(query = route.query) {
  const raw = query.workId
  if (raw == null || raw === '') return
  const id = Number(raw)
  if (!Number.isFinite(id) || id <= 0) {
    router.replace({ name: 'square', query: {} })
    return
  }
  await nextTick()
  const w = works.value.find((x) => Number(x.work_id) === id)
  if (w) {
    await openComments(w)
    router.replace({ name: 'square', query: {} })
  } else {
    alert('该作品已不在公开展示中，无法从照片展示打开')
    router.replace({ name: 'square', query: {} })
  }
}

onMounted(async () => {
  await reload()
  await tryOpenWorkFromQuery()
})

onBeforeRouteUpdate(async (to) => {
  const wid = to.query?.workId
  if (wid == null || wid === '') return
  if (!works.value.length) await reload()
  await tryOpenWorkFromQuery(to.query)
})

function onPickFile(e) {
  const f = e?.target?.files?.[0]
  form.value.image = f || null
}

function openCreate() {
  if (!isLoggedIn()) {
    goLogin(router, route.fullPath)
    return
  }
  showCreate.value = true
}

function closeCreate() {
  showCreate.value = false
  creating.value = false
}

async function submit() {
  if (!isLoggedIn()) {
    goLogin(router, route.fullPath)
    return
  }
  if (!form.value.image) {
    alert('请选择图片')
    return
  }
  const required = ['camera_name', 'lens_name', 'iso', 'shutter_speed', 'aperture', 'shoot_location']
  for (const k of required) {
    if (!String(form.value[k] || '').trim()) {
      alert('请完整填写参数与地点')
      return
    }
  }
  creating.value = true
  try {
    const fd = new FormData()
    fd.append('image', form.value.image)
    fd.append('camera_name', form.value.camera_name)
    fd.append('lens_name', form.value.lens_name)
    fd.append('iso', form.value.iso)
    fd.append('shutter_speed', form.value.shutter_speed)
    fd.append('aperture', form.value.aperture)
    fd.append('shoot_location', form.value.shoot_location)
    await createWork(fd)
    alert('发布成功，等待管理员审核通过后将出现在照片展示中')
    closeCreate()
    form.value = { image: null, camera_name: '', lens_name: '', iso: '', shutter_speed: '', aperture: '', shoot_location: '' }
    await reload()
  } catch (e) {
    alert(e?.message || '发布失败')
  } finally {
    creating.value = false
  }
}

async function openComments(w) {
  commentModalWork.value = w
  newComment.value = ''
  await loadCommentsForModal(w.work_id)
}

function closeCommentModal() {
  commentModalWork.value = null
  comments.value = []
}

async function loadCommentsForModal(workId) {
  commentLoading.value = true
  try {
    const res = await fetchWorkComments(workId)
    comments.value = res?.data || []
  } catch (e) {
    alert(e?.message || '加载评论失败')
    comments.value = []
  } finally {
    commentLoading.value = false
  }
}

async function submitComment() {
  if (!isLoggedIn()) {
    goLogin(router, route.fullPath)
    return
  }
  const w = commentModalWork.value
  if (!w) return
  const t = newComment.value.trim()
  if (!t) return
  commentSubmitting.value = true
  try {
    await postWorkComment(w.work_id, t)
    newComment.value = ''
    await loadCommentsForModal(w.work_id)
    await reload()
  } catch (e) {
    alert(e?.message || '发送失败')
  } finally {
    commentSubmitting.value = false
  }
}

function canDeleteComment(c) {
  return Number(c.user_id) === currentUserId.value || isAdminUser.value
}

async function removeComment(c) {
  const w = commentModalWork.value
  if (!w) return
  if (!confirm('确定删除该评论？')) return
  try {
    await deleteWorkComment(w.work_id, c.comment_id)
    await loadCommentsForModal(w.work_id)
    await reload()
  } catch (e) {
    alert(e?.message || '删除失败')
  }
}

function openWorkImageLightbox(w) {
  if (!w?.image_url) return
  imageLightboxSrc.value = w.image_url
  imageLightboxAlt.value = `${userName(w)} · ${w.shoot_location || '作品'}`
  imageLightboxOpen.value = true
}
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">照片展示</div>
      <div class="actions">
        <button class="btn primary" type="button" @click="openCreate">发布作品</button>
      </div>
    </div>

    <div v-if="loading" class="hint">加载中…</div>
    <div v-else-if="works.length === 0" class="hint">暂无作品（仅展示管理员已审核通过的作品）</div>

    <div class="grid" v-else>
      <article v-for="w in works" :key="w.work_id" class="card">
        <div class="img">
          <img
            class="img__thumb"
            :src="w.image_url"
            alt="作品图片，点击放大"
            role="button"
            tabindex="0"
            @click="openWorkImageLightbox(w)"
            @keydown.enter.prevent="openWorkImageLightbox(w)"
            @keydown.space.prevent="openWorkImageLightbox(w)"
          />
          <button type="button" class="btn-comment" @click.stop="openComments(w)">
            评论<span v-if="Number(w.comment_count) > 0" class="btn-comment__cnt">{{ w.comment_count }}</span>
          </button>
        </div>
        <div class="meta">
          <div class="author">
            <img class="avatar" :src="userAvatar(w)" alt="avatar" />
            <div class="who">
              <div class="name">{{ userName(w) }}</div>
              <div class="sub">{{ w.shoot_location }}</div>
            </div>
          </div>
          <div class="params">
            <div class="row"><span class="k">相机</span><span class="v">{{ w.camera_name }}</span></div>
            <div class="row"><span class="k">镜头</span><span class="v">{{ w.lens_name }}</span></div>
            <div class="row"><span class="k">ISO</span><span class="v">{{ w.iso }}</span></div>
            <div class="row"><span class="k">曝光</span><span class="v">{{ w.shutter_speed }}</span></div>
            <div class="row"><span class="k">光圈</span><span class="v">{{ w.aperture }}</span></div>
          </div>
        </div>
      </article>
    </div>

    <div v-if="showCreate" class="mask" @click.self="closeCreate">
      <div class="modal">
        <div class="modal__head">
          <div class="modal__title">发布作品</div>
          <button class="x" type="button" @click="closeCreate">×</button>
        </div>

        <div class="form">
          <label class="field">
            <div class="lbl">上传图片</div>
            <input type="file" accept="image/*" @change="onPickFile" />
          </label>
          <label class="field">
            <div class="lbl">相机名称</div>
            <input v-model="form.camera_name" type="text" placeholder="如：Sony A7M4" />
          </label>
          <label class="field">
            <div class="lbl">镜头名称</div>
            <input v-model="form.lens_name" type="text" placeholder="如：24-70mm F2.8" />
          </label>
          <div class="row2">
            <label class="field">
              <div class="lbl">ISO</div>
              <input v-model="form.iso" type="text" placeholder="如：800" />
            </label>
            <label class="field">
              <div class="lbl">曝光时间</div>
              <input v-model="form.shutter_speed" type="text" placeholder="如：1/200s" />
            </label>
          </div>
          <label class="field">
            <div class="lbl">光圈大小</div>
            <input v-model="form.aperture" type="text" placeholder="如：F2.8" />
          </label>
          <label class="field">
            <div class="lbl">拍摄地点</div>
            <input v-model="form.shoot_location" type="text" placeholder="如：武汉·东湖" />
          </label>
        </div>

        <div class="foot">
          <button class="btn" type="button" :disabled="creating" @click="closeCreate">取消</button>
          <button class="btn primary" type="button" :disabled="creating" @click="submit">
            {{ creating ? '发布中…' : '发布' }}
          </button>
        </div>
      </div>
    </div>

    <ImageLightbox
      v-model:open="imageLightboxOpen"
      :src="imageLightboxSrc"
      :alt="imageLightboxAlt"
    />

    <div v-if="commentModalWork" class="mask" @click.self="closeCommentModal">
      <div class="modal modal--comments">
        <div class="modal__head">
          <div class="modal__title">评论 · {{ commentModalWork.shoot_location }}</div>
          <button class="x" type="button" @click="closeCommentModal">×</button>
        </div>
        <div class="comments-wrap">
          <p class="comments-tip">发表评论后需管理员审核通过才会对所有人展示；您始终可查看自己的评论及状态。</p>
          <div v-if="commentLoading" class="hint">加载中…</div>
          <div v-else-if="!comments.length" class="hint">暂无评论</div>
          <div v-else class="comment-list">
            <div v-for="c in comments" :key="c.comment_id" class="comment-item">
              <img class="c-av" :src="c.user?.avatar_url || defaultUserImg" alt="" />
              <div class="c-body">
                <div class="c-meta">
                  <span class="c-name">{{ c.user?.username || `用户${c.user_id}` }}</span>
                  <span class="c-time">{{ formatOrderDateTime(c.created_at) }}</span>
                  <span v-if="c.status !== '已通过'" class="c-status">{{ c.status }}</span>
                </div>
                <div class="c-text">{{ c.content }}</div>
              </div>
              <button
                v-if="canDeleteComment(c)"
                type="button"
                class="c-del"
                @click="removeComment(c)"
              >
                删除
              </button>
            </div>
          </div>
          <div class="comment-form">
            <textarea
              v-model="newComment"
              rows="3"
              maxlength="2000"
              placeholder="写下评论…"
            ></textarea>
            <button
              class="btn primary"
              type="button"
              :disabled="commentSubmitting || !newComment.trim()"
              @click="submitComment"
            >
              {{ commentSubmitting ? '发送中…' : '发布评论' }}
            </button>
          </div>
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
.hint {
  opacity: 0.75;
  padding: 24px 8px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 980px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 620px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
.card {
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.6);
}
.img {
  position: relative;
  aspect-ratio: 4 / 3;
  background: rgba(148, 163, 184, 0.12);
}
.img img,
.img__thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.img__thumb {
  cursor: zoom-in;
}
.img__thumb:focus-visible {
  outline: 2px solid rgba(99, 102, 241, 0.65);
  outline-offset: 2px;
}
.btn-comment {
  position: absolute;
  right: 10px;
  bottom: 10px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.45);
  background: rgba(15, 23, 42, 0.55);
  color: #fff;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
  backdrop-filter: blur(6px);
}
.btn-comment:hover {
  background: rgba(15, 23, 42, 0.72);
}
.btn-comment__cnt {
  min-width: 1.2em;
  text-align: center;
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
}
.modal--comments {
  width: min(520px, 100%);
  max-height: min(86vh, 720px);
  display: flex;
  flex-direction: column;
}
.comments-wrap {
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  min-height: 0;
  flex: 1;
}
.comments-tip {
  font-size: 12px;
  opacity: 0.72;
  line-height: 1.45;
  margin: 0;
}
.comment-list {
  overflow-y: auto;
  max-height: 320px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-right: 4px;
}
.comment-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(148, 163, 184, 0.08);
}
.c-av {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  object-fit: cover;
  flex-shrink: 0;
}
.c-body {
  flex: 1;
  min-width: 0;
}
.c-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 4px;
}
.c-name {
  font-weight: 900;
}
.c-time {
  opacity: 0.65;
  font-family: ui-monospace, monospace;
  font-size: 11px;
}
.c-status {
  font-size: 11px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(234, 179, 8, 0.2);
  color: #92400e;
}
.c-text {
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.c-del {
  flex-shrink: 0;
  border: 1px solid rgba(220, 38, 38, 0.35);
  background: rgba(220, 38, 38, 0.08);
  color: #b91c1c;
  border-radius: 10px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}
.comment-form textarea {
  width: 100%;
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 12px;
  padding: 10px 12px;
  resize: vertical;
  min-height: 72px;
  margin-bottom: 10px;
  font-family: inherit;
}
.comment-form .btn.primary {
  width: 100%;
}
.meta {
  padding: 12px;
}
.author {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  object-fit: cover;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(148, 163, 184, 0.14);
}
.who .name {
  font-weight: 900;
  line-height: 1.1;
}
.who .sub {
  font-size: 12px;
  opacity: 0.75;
  margin-top: 2px;
}
.params {
  display: grid;
  gap: 6px;
  font-size: 13px;
}
.params .row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.params .k {
  opacity: 0.7;
}
.params .v {
  font-weight: 800;
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
  width: min(620px, 100%);
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
.form {
  padding: 14px;
  display: grid;
  gap: 10px;
}
.field .lbl {
  font-size: 12px;
  opacity: 0.75;
  margin-bottom: 6px;
}
.field input {
  width: 100%;
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 12px;
  padding: 10px 12px;
  outline: none;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
@media (max-width: 520px) {
  .row2 {
    grid-template-columns: 1fr;
  }
}
.foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 14px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}
</style>

