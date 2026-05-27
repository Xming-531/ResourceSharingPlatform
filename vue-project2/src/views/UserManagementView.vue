<script setup>
import { onMounted, ref } from 'vue'
import { adminDeleteUser, adminDisableUser, adminListUsers, adminResetUserPassword } from '@/api/admin'

const users = ref([])
const loading = ref(false)

async function reload() {
  loading.value = true
  try {
    const res = await adminListUsers()
    users.value = res?.data || []
  } catch (e) {
    alert(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(reload)

async function onToggle(u) {
  try {
    await adminDisableUser(u.id, !u.enabled)
    await reload()
  } catch (e) {
    alert(e?.message || '操作失败')
  }
}

async function onDelete(u) {
  try {
    if (!confirm(`确定删除用户 ${u.username} 吗？`)) return
    await adminDeleteUser(u.id)
    await reload()
  } catch (e) {
    alert(e?.message || '删除失败')
  }
}

async function onResetPassword(u) {
  if (!confirm(`确定将用户「${u.username}」的密码重置为 123？该用户需重新登录。`)) return
  try {
    const res = await adminResetUserPassword(u.id)
    alert(res?.message || '密码已重置为 123')
    await reload()
  } catch (e) {
    alert(e?.message || '重置失败')
  }
}
</script>

<template>
  <section class="page">
    <div class="head">
      <div class="title">用户管理</div>
      <div class="sub">只有管理员账号可进入此页面。</div>
    </div>

    <div class="table">
      <div class="tr th">
        <div>用户名</div>
        <div>角色</div>
        <div>状态</div>
        <div>操作</div>
      </div>
      <div v-if="loading" class="tr"><div>加载中...</div></div>
      <div v-for="u in users" :key="u.id" class="tr">
        <div class="name">{{ u.username }}</div>
        <div><span class="tag">{{ u.role }}</span></div>
        <div>{{ u.enabled ? '正常' : '禁用' }}</div>
        <div class="ops">
          <button class="btn" type="button" @click="onResetPassword(u)">重置密码</button>
          <button class="btn" type="button" @click="onDelete(u)">删除</button>
          <button class="btn danger" type="button" @click="onToggle(u)">{{ u.enabled ? '禁用' : '启用' }}</button>
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
  padding: 6px 6px 14px;
}
.title {
  font-size: 18px;
  font-weight: 900;
}
.sub {
  font-size: 13px;
  opacity: 0.7;
  margin-top: 4px;
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
  grid-template-columns: 1fr 140px 120px minmax(280px, 1fr);
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}
.tr.th {
  border-top: 0;
  font-weight: 900;
  background: rgba(148, 163, 184, 0.14);
}
.name {
  font-weight: 900;
}
.tag {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(99, 102, 241, 0.25);
  background: rgba(99, 102, 241, 0.12);
  font-weight: 800;
}
.ops {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
.btn {
  border: 1px solid rgba(15, 23, 42, 0.14);
  background: rgba(255, 255, 255, 0.4);
  color: inherit;
  border-radius: 12px;
  padding: 8px 10px;
  cursor: pointer;
  font-weight: 800;
}
.btn.danger {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.1);
}
@media (max-width: 980px) {
  .tr {
    grid-template-columns: 1fr;
  }
  .tr.th {
    display: none;
  }
  .ops {
    justify-content: flex-start;
  }
}
</style>

