<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, unwrap } from '@/api/client'
import { deleteMyAccount } from '@/api/auth'
import { clearSession, getSession, setSession } from '@/utils/session'
import defaultUserImg from '@/assets/default_user_img.png'

const router = useRouter()

const session = ref(getSession())
const user = computed(() => session.value?.user || { username: '游客', phone: '', identity_verified: false })
const identityLabel = computed(() => (user.value?.identity_verified ? '是' : '否'))
const role = computed(() => session.value?.role || 'user')
const avatarSrc = computed(() => user.value?.avatar_url || defaultUserImg)
const uploading = ref(false)
const avatarFile = ref(null)
const deletingAccount = ref(false)

async function loadMe() {
  const res = unwrap(await api.get('/api/me'))
  if (!res?.ok) return
  const s = getSession()
  if (!s?.token) return
  const nextUser = res.data
  const nextRole = String(nextUser?.role) === '0' ? 'admin' : 'user'
  setSession({ ...s, user: nextUser, role: nextRole })
  session.value = getSession()
}

onMounted(() => {
  loadMe().catch(() => null)
})

function onAvatarChange(e) {
  avatarFile.value = e?.target?.files?.[0] || null
}

async function uploadAvatar() {
  if (!avatarFile.value) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('avatar', avatarFile.value)
    const res = unwrap(await api.patch('/api/me/avatar', fd, { headers: { 'Content-Type': 'multipart/form-data' } }))
    if (!res?.ok) {
      alert(res?.message || '上传失败')
      return
    }
    avatarFile.value = null
    await loadMe()
    alert('头像已更新')
  } catch (e) {
    alert(e?.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function verifyIdentity() {
  if (user.value?.identity_verified) return
  try {
    const res = unwrap(await api.post('/api/me/identity-verify', {}))
    if (!res?.ok) {
      alert(res?.message || '操作失败')
      return
    }
    await loadMe()
    alert(res?.message || '实名认证成功')
  } catch (e) {
    alert(e?.message || '请求失败')
  }
}

async function changePhone() {
  const next = prompt('修改电话', user.value.phone || '')
  if (!next) return
  const res = unwrap(await api.patch('/api/me/phone', { phone: next }))
  if (!res?.ok) alert(res?.message || '修改失败')
  await loadMe()
}

async function changePassword() {
  const oldPassword = prompt('原密码')
  if (!oldPassword) return
  const newPassword = prompt('新密码')
  if (!newPassword) return
  const res = unwrap(await api.patch('/api/me/password', { old_password: oldPassword, new_password: newPassword }))
  if (!res?.ok) {
    alert(res?.message || '修改失败')
    return
  }
  alert(res?.message || '密码已修改，请重新登录')
  clearSession()
  window.location.href = '/auth'
}

async function onDeleteAccount() {
  if (role.value === 'admin') return
  const ok = window.confirm(
    '注销后将永久删除您的账户数据且无法恢复（未完成订单时无法注销）。确定要注销吗？',
  )
  if (!ok) return
  deletingAccount.value = true
  try {
    const res = await deleteMyAccount()
    if (!res?.ok) {
      alert(res?.message || '注销失败')
      return
    }
    clearSession()
    window.dispatchEvent(new Event('session-changed'))
    await router.replace({ name: 'home' })
  } catch (e) {
    alert(e?.message || '注销失败')
  } finally {
    deletingAccount.value = false
  }
}
</script>

<template>
  <section class="page">
    <div class="card">
      <div class="title">个人信息管理</div>
      <div class="avatarBox">
        <img class="avatar" :src="avatarSrc" alt="avatar" />
        <div class="avatarBox__actions">
          <input type="file" accept="image/*" :disabled="uploading" @change="onAvatarChange" />
          <button class="btn" type="button" :disabled="uploading || !avatarFile" @click="uploadAvatar">
            {{ uploading ? '上传中…' : '上传头像' }}
          </button>
          <div class="hint">未上传时默认使用系统头像</div>
        </div>
      </div>
      <div class="row"><span class="k">用户名</span><span class="v">{{ user.username }}</span></div>
      <div class="row"><span class="k">实名状态</span><span class="v">{{ identityLabel }}</span></div>
      <div class="row"><span class="k">电话</span><span class="v">{{ user.phone }}</span></div>
      <div class="row"><span class="k">角色</span><span class="v">{{ role === 'admin' ? '管理员' : '用户' }}</span></div>
      <div class="btnRow">
        <button
          class="btn btn--primary"
          type="button"
          :disabled="!!user.identity_verified"
          @click="verifyIdentity"
        >
          {{ user.identity_verified ? '已实名' : '实名认证' }}
        </button>
        <button class="btn" type="button" @click="changePhone">修改电话</button>
      </div>
      <button class="btn btn--block" type="button" @click="changePassword">修改密码</button>

      <div v-if="role !== 'admin'" class="dangerZone">
        <div class="dangerZone__title">危险操作</div>
        <button
          class="btn btn--danger btn--block"
          type="button"
          :disabled="deletingAccount"
          @click="onDeleteAccount"
        >
          {{ deletingAccount ? '处理中…' : '注销账户' }}
        </button>
        <div class="hint dangerZone__hint">
          注销后将清除您上传的商品、作品、评论、收藏与账单消息，关联订单将从对方列表中移除；有进行中的订单时需先完成后再注销。
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.page {
  padding: 4px;
}
.card {
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  padding: 16px;
}
@media (prefers-color-scheme: dark) {
  .card {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}
.title {
  font-size: 18px;
  font-weight: 900;
  margin-bottom: 12px;
}

.avatarBox {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 12px 0 14px;
  border-bottom: 1px dashed rgba(15, 23, 42, 0.12);
  margin-bottom: 6px;
}

.avatar {
  width: 72px;
  height: 72px;
  border-radius: 999px;
  object-fit: cover;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(148, 163, 184, 0.14);
}

.avatarBox__actions {
  display: grid;
  gap: 8px;
  flex: 1;
}

.hint {
  font-size: 12px;
  opacity: 0.7;
}
.row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px dashed rgba(15, 23, 42, 0.12);
}
.k {
  opacity: 0.75;
}
.v {
  font-weight: 900;
}
.btnRow {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
  align-items: center;
}
.btn {
  margin-top: 0;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.4);
  color: inherit;
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 800;
}
.btn--primary {
  border-color: rgba(37, 99, 235, 0.35);
  background: rgba(37, 99, 235, 0.12);
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn--block {
  margin-top: 12px;
  display: block;
  width: 100%;
  max-width: 320px;
}

.dangerZone {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed rgba(239, 68, 68, 0.35);
}
.dangerZone__title {
  font-size: 13px;
  font-weight: 800;
  color: #b91c1c;
  margin-bottom: 10px;
}
.btn--danger {
  border-color: rgba(239, 68, 68, 0.45);
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
}
.btn--danger:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.16);
}
.dangerZone__hint {
  margin-top: 8px;
  max-width: 420px;
}
@media (prefers-color-scheme: dark) {
  .dangerZone__title {
    color: #f87171;
  }
  .btn--danger {
    color: #fca5a5;
    border-color: rgba(248, 113, 113, 0.4);
    background: rgba(239, 68, 68, 0.12);
  }
}
</style>

