<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchAdminSupportPhone, login, register } from '@/api/auth'
import { setSession } from '@/utils/session'

const route = useRoute()
const router = useRouter()

const mode = ref(route.query.mode === 'register' ? 'register' : 'login')
const busy = ref(false)
const errorMsg = ref('')

const loginFailCount = ref(0)
const loginFailUsername = ref('')
const adminSupportPhone = ref('')

onMounted(() => {
  fetchAdminSupportPhone()
    .then((r) => {
      const p = r?.data?.phone
      if (typeof p === 'string' && p.trim()) adminSupportPhone.value = p.trim()
    })
    .catch(() => {})
})

const loginForm = reactive({
  username: '',
  password: '',
})

const registerForm = reactive({
  username: '',
  phone: '',
  password: '',
  confirmPassword: '',
})

const canSubmit = computed(() => {
  if (busy.value) return false
  if (mode.value === 'login') return Boolean(loginForm.username && loginForm.password)
  return Boolean(registerForm.username && registerForm.phone && registerForm.password && registerForm.confirmPassword)
})

function switchMode(next) {
  errorMsg.value = ''
  loginFailCount.value = 0
  loginFailUsername.value = ''
  mode.value = next
  router.replace({ query: { ...route.query, mode: next } })
}

watch(
  () => loginForm.username,
  (u) => {
    const next = String(u || '').trim()
    if (next !== loginFailUsername.value) {
      loginFailCount.value = 0
      loginFailUsername.value = next
    }
  },
)

async function onSubmit() {
  errorMsg.value = ''
  busy.value = true
  try {
    if (mode.value === 'register') {
      if (registerForm.password !== registerForm.confirmPassword) {
        errorMsg.value = '两次密码不一致'
        return
      }
      const res = await register({
        username: registerForm.username,
        phone: registerForm.phone,
        password: registerForm.password,
      })
      if (!res?.ok) {
        errorMsg.value = res?.message || '注册失败'
        return
      }
      errorMsg.value = '注册成功，请登录'
      switchMode('login')
      return
    }

    const res = await login({ username: loginForm.username, password: loginForm.password })
    if (!res?.ok) {
      errorMsg.value = res?.message || '登录失败'
      return
    }

    const token = res?.data?.token
    const user = res?.data?.user
    const role = String(user?.role) === '0' ? 'admin' : 'user'
    setSession({ token, user, role })
    loginFailCount.value = 0
    loginFailUsername.value = ''

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/home'
    await router.replace(redirect)
  } catch (e) {
    const msg = e?.message || '请求失败，请稍后重试'
    // 401 会进入 catch，这里处理连续密码错误计数
    if (mode.value === 'login' && msg === '用户名或密码错误') {
      const uname = String(loginForm.username || '').trim()
      if (loginFailUsername.value !== uname) {
        loginFailUsername.value = uname
        loginFailCount.value = 0
      }
      loginFailCount.value += 1
      if (loginFailCount.value >= 3) {
        const tel = adminSupportPhone.value
        errorMsg.value = tel
          ? `如果密码遗忘请联系管理员（tel:${tel}）重置`
          : '如果密码遗忘请联系管理员重置'
      } else {
        errorMsg.value = msg
      }
      return
    }
    errorMsg.value = msg
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="auth">
    <div class="bg" aria-hidden="true"></div>

    <div class="card">
      <div class="brand">
        <div class="logo">
          <img src="/src/images/logo.png" class="logo_png" alt="logo">
        </div>
        <div class="title">
          <div class="name">摄影资源交易平台</div>
          <div class="desc">租借 · 交易 · 收藏 · 管理</div>
        </div>
      </div>

      <div class="tabs" role="tablist" aria-label="登录注册切换">
        <button
          class="tab"
          :class="{ active: mode === 'login' }"
          type="button"
          role="tab"
          :aria-selected="mode === 'login'"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          class="tab"
          :class="{ active: mode === 'register' }"
          type="button"
          role="tab"
          :aria-selected="mode === 'register'"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <form class="form" @submit.prevent="onSubmit">
        <div class="field">
          <label>{{ mode === 'login' ? '用户名' : '用户名' }}</label>
          <input
            v-if="mode === 'login'"
            v-model.trim="loginForm.username"
            autocomplete="username"
            placeholder="请输入用户名"
            :disabled="busy"
          />
          <input
            v-else
            v-model.trim="registerForm.username"
            autocomplete="username"
            placeholder="请输入用户名"
            :disabled="busy"
          />
        </div>

        <div v-if="mode === 'register'" class="field">
          <label>电话</label>
          <input v-model.trim="registerForm.phone" autocomplete="tel" placeholder="请输入电话" :disabled="busy" />
        </div>

        <div class="field">
          <label>密码</label>
          <input
            v-if="mode === 'login'"
            v-model="loginForm.password"
            type="password"
            autocomplete="current-password"
            placeholder="请输入密码"
            :disabled="busy"
          />
          <input
            v-else
            v-model="registerForm.password"
            type="password"
            autocomplete="new-password"
            placeholder="请输入密码"
            :disabled="busy"
          />
        </div>

        <div v-if="mode === 'register'" class="field">
          <label>确认密码</label>
          <input
            v-model="registerForm.confirmPassword"
            type="password"
            autocomplete="new-password"
            placeholder="再次输入密码"
            :disabled="busy"
          />
        </div>

        <div v-if="errorMsg" class="alert" :class="{ success: errorMsg.includes('成功') }">
          {{ errorMsg }}
        </div>

        <button class="submit" type="submit" :disabled="!canSubmit">
          <span v-if="busy">处理中...</span>
          <span v-else>{{ mode === 'login' ? '登录' : '注册' }}</span>
        </button>

        <div class="foot">
          <span v-if="mode === 'login'">
            还没有账号？
            <a href="#" @click.prevent="switchMode('register')">去注册</a>
          </span>
          <span v-else>
            已有账号？
            <a href="#" @click.prevent="switchMode('login')">去登录</a>
          </span>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.auth {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 16px;
  position: relative;
  overflow: hidden;
}

.bg {
  position: absolute;
  inset: -40% -20%;
  background:
    radial-gradient(40% 40% at 20% 20%, rgba(99, 102, 241, 0.35) 0%, transparent 60%),
    radial-gradient(35% 35% at 80% 30%, rgba(16, 185, 129, 0.25) 0%, transparent 60%),
    radial-gradient(40% 40% at 55% 85%, rgba(59, 130, 246, 0.22) 0%, transparent 60%),
    linear-gradient(180deg, rgba(2, 6, 23, 0.04), rgba(2, 6, 23, 0.02));
  filter: blur(10px);
  transform: rotate(-8deg);
  pointer-events: none;
}

.card {
  width: min(420px, 100%);
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  box-shadow: 0 30px 80px rgba(2, 6, 23, 0.18);
  backdrop-filter: blur(10px);
  padding: 18px;
  position: relative;
}

@media (prefers-color-scheme: dark) {
  .card {
    background: rgba(17, 24, 39, 0.72);
    border-color: rgba(148, 163, 184, 0.18);
    box-shadow: 0 30px 90px rgba(0, 0, 0, 0.45);
  }
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 6px 6px 10px;
}

.logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  overflow: hidden;
}

.logo_png{
  width: 48px;
  height: 48px;
}

.title .name {
  font-weight: 800;
  font-size: 16px;
  line-height: 1.2;
}

.title .desc {
  font-size: 12px;
  opacity: 0.72;
}

.tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  background: rgba(148, 163, 184, 0.14);
  border-radius: 12px;
  padding: 6px;
  margin-top: 10px;
}

.tab {
  border: 0;
  background: transparent;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 700;
  color: inherit;
  opacity: 0.8;
}

.tab.active {
  background: rgba(255, 255, 255, 0.85);
  opacity: 1;
  box-shadow: 0 10px 20px rgba(2, 6, 23, 0.12);
}

@media (prefers-color-scheme: dark) {
  .tab.active {
    background: rgba(30, 41, 59, 0.8);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.25);
  }
}

.form {
  margin-top: 14px;
  display: grid;
  gap: 12px;
  padding: 6px;
}

.field {
  display: grid;
  gap: 6px;
}

label {
  font-size: 12px;
  opacity: 0.75;
}

input,
select {
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  padding: 11px 12px;
  outline: none;
  background: rgba(255, 255, 255, 0.75);
  color: inherit;
}

@media (prefers-color-scheme: dark) {
  input,
  select {
    border-color: rgba(148, 163, 184, 0.22);
    background: rgba(15, 23, 42, 0.35);
  }
}

input:focus,
select:focus {
  border-color: rgba(99, 102, 241, 0.8);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
}

.hint {
  font-size: 12px;
  color: #ef4444;
}

.alert {
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
  border: 1px solid rgba(239, 68, 68, 0.28);
  background: rgba(239, 68, 68, 0.08);
  color: inherit;
}

.alert.success {
  border-color: rgba(34, 197, 94, 0.32);
  background: rgba(34, 197, 94, 0.1);
}

.submit {
  border: 0;
  border-radius: 12px;
  padding: 12px 12px;
  font-weight: 800;
  cursor: pointer;
  color: white;
  background: linear-gradient(135deg, #6366f1, #3b82f6);
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.25);
}

.submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

.foot {
  text-align: center;
  font-size: 13px;
  opacity: 0.85;
  padding-top: 2px;
}

a {
  color: inherit;
  font-weight: 800;
}
</style>

