<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { clearSession, getSession, isAdmin as isAdminSession, isLoggedIn } from '@/utils/session'
import { goLogin } from '@/utils/authNavigate'
import { logout } from '@/api/auth'
import defaultUserImg from '@/assets/default_user_img.png'

const route = useRoute()
const router = useRouter()

const sessionTick = ref(0)
function bumpSessionTick() {
  sessionTick.value++
}
onMounted(() => {
  window.addEventListener('session-changed', bumpSessionTick)
})
onUnmounted(() => {
  window.removeEventListener('session-changed', bumpSessionTick)
})

const loggedIn = computed(() => {
  void sessionTick.value
  return isLoggedIn()
})

const user = computed(() => {
  void sessionTick.value
  const s = getSession()
  return s?.user || null
})
const isAdmin = computed(() => isAdminSession())
const avatarSrc = computed(() => (loggedIn.value ? user.value?.avatar_url : null) || defaultUserImg)

const menu = computed(() => {
  const common = [
    { name: 'home', label: '首页展示', icon: '🏠' },
    { name: 'square', label: '照片展示', icon: '🖼️' },
    { name: 'myWorks', label: '我的作品', icon: '🎨' },
    { name: 'myWorkComments', label: '评论管理', icon: '💬' },
    { name: 'profile', label: '个人信息', icon: '👤' },
    { name: 'orders', label: '订单管理', icon: '🧾' },
    { name: 'billingMessages', label: '账单消息', icon: '💳' },
    { name: 'myResources', label: '个人资源', icon: '📦' },
  ]

  const admin = [
    { name: 'adminDashboard', label: '首页展示', icon: '🏠', adminOnly: true },
    { name: 'adminMarquee', label: '精选展示', icon: '🎠', adminOnly: true },
    { name: 'users', label: '用户管理', icon: '🛡️', adminOnly: true },
    { name: 'adminResources', label: '资源管理', icon: '🗂️', adminOnly: true },
    { name: 'adminWorks', label: '作品审核', icon: '✅', adminOnly: true },
    { name: 'adminWorkComments', label: '评论管理', icon: '💬', adminOnly: true },
  ]

  // 管理员：不展示用户端首页/照片展示/我的作品/个人资源/账单消息/收藏；另有独立「首页展示」看板
  if (isAdmin.value) {
    const hide = new Set(['home', 'square', 'myWorks', 'myWorkComments', 'myResources', 'billingMessages'])
    return [...admin.slice(0, 1), ...common.filter((m) => !hide.has(m.name)), ...admin.slice(1)]
  }
  return [...common, { name: 'favorites', label: '收藏管理', icon: '⭐' }]
})

function onLogout() {
  Promise.resolve()
    .then(() => logout())
    .catch(() => null)
    .finally(() => {
      clearSession()
      router.replace({ name: 'auth' })
    })
}

function onGoLogin() {
  goLogin(router, route.fullPath)
}

const pageTitle = computed(() => {
  const found = menu.value.find((m) => m.name === route.name)
  return found?.label || '摄影资源分享平台'
})
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <div class="topbar__inner">
        <div class="brand">
          <div class="logo" aria-hidden="true">
            <img src="/src/images/logo.png" alt="logo" class="logo_png">
          </div>
          <div class="brand__text">
            <div class="brand__name">摄影资源分享平台</div>
            <div class="brand__sub">{{ pageTitle }}</div>
          </div>
        </div>

        <div class="userbox">
          <img class="avatar" :src="avatarSrc" alt="avatar" />
          <div class="userbox__meta">
            <template v-if="loggedIn">
              <div class="userbox__name">{{ user?.username || user?.phone || '用户' }}</div>
              <div class="userbox__role">{{ isAdmin ? '管理员' : '用户' }}</div>
            </template>
            <template v-else>
              <div class="userbox__name">游客</div>
              <div class="userbox__role">游客</div>
            </template>
          </div>
          <button v-if="loggedIn" class="btn" type="button" @click="onLogout">退出</button>
          <button v-else class="btn btn--primary" type="button" @click="onGoLogin">登录</button>
        </div>
      </div>
    </header>

    <div class="content">
      <aside class="sidebar">
        <nav class="nav" aria-label="侧边菜单">
          <RouterLink
            v-for="m in menu"
            :key="m.name"
            class="item"
            :class="{ active: route.name === m.name }"
            :to="{ name: m.name }"
          >
            <span class="icon" aria-hidden="true">{{ m.icon }}</span>
            <span class="label">{{ m.label }}</span>
          </RouterLink>
        </nav>
      </aside>

      <main class="main">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
}

@media (prefers-color-scheme: dark) {
  .topbar {
    background: rgba(2, 6, 23, 0.45);
    border-bottom-color: rgba(148, 163, 184, 0.16);
  }
}

.topbar__inner {
  max-width: 1240px;
  margin: 0 auto;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 240px;
}

.logo {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  overflow: hidden;
  display: grid;
  place-items: center;
  color: white;
  font-weight: 900;
  background: linear-gradient(135deg, #6366f1, #22c55e);
}

.logo_png{
  width: 42px;
  height: 42px;
}

.brand__name {
  font-weight: 900;
  line-height: 1.2;
}

.brand__sub {
  font-size: 13px;
  opacity: 0.7;
  margin-top: 2px;
}

.userbox {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 999px;
  object-fit: cover;
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(148, 163, 184, 0.14);
  flex-shrink: 0;
}

.userbox__meta {
  text-align: right;
}

.userbox__name {
  font-weight: 900;
  line-height: 1.1;
}

.userbox__role {
  font-size: 12px;
  opacity: 0.7;
  margin-top: 2px;
}

.btn {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.4);
  color: inherit;
  border-radius: 12px;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 800;
}

.btn--primary {
  border-color: rgba(99, 102, 241, 0.35);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.95), rgba(59, 130, 246, 0.95));
  color: #fff;
}

.content {
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
  padding: 16px;
  display: grid;
  /* 大屏：侧边菜单缩小为约 2/3 */
  grid-template-columns: 174px 1fr;
  gap: 16px;
  align-items: start;
}

.sidebar {
  position: sticky;
  top: 76px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(8px);
  padding: 12px;
}

@media (prefers-color-scheme: dark) {
  .sidebar {
    background: rgba(15, 23, 42, 0.28);
    border-color: rgba(148, 163, 184, 0.18);
  }
}

.nav {
  display: grid;
  gap: 8px;
}

.item {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: rgba(255, 255, 255, 0.35);
  border-radius: 12px;
  padding: 10px 12px;
  font-weight: 800;
  opacity: 0.9;
}

.item.active {
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12);
  background: rgba(99, 102, 241, 0.12);
  opacity: 1;
}

.icon {
  width: 22px;
  display: inline-flex;
  justify-content: center;
}

.main {
  min-width: 0;
}

@media (max-width: 980px) {
  .content {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: relative;
    top: auto;
  }

  .userbox__meta {
    display: none;
  }
}
</style>

