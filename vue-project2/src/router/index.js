import { createRouter, createWebHistory } from 'vue-router'
import { isAdmin, isLoggedIn } from '@/utils/session'

import AuthView from '@/views/AuthView.vue'
import MainLayout from '@/views/MainLayout.vue'
import HomeView from '@/views/HomeView.vue'
import ProfileView from '@/views/ProfileView.vue'
import OrdersView from '@/views/OrdersView.vue'
import BillingMessagesView from '@/views/BillingMessagesView.vue'
import FavoritesView from '@/views/FavoritesView.vue'
import MyResourcesView from '@/views/MyResourcesView.vue'
import UserManagementView from '@/views/UserManagementView.vue'
import AdminResourcesView from '@/views/AdminResourcesView.vue'
import WorksSquareView from '@/views/WorksSquareView.vue'
import MyWorksView from '@/views/MyWorksView.vue'
import MyWorkCommentsView from '@/views/MyWorkCommentsView.vue'
import AdminWorksView from '@/views/AdminWorksView.vue'
import AdminWorkCommentsView from '@/views/AdminWorkCommentsView.vue'
import AdminDashboardView from '@/views/AdminDashboardView.vue'
import AdminMarqueeView from '@/views/AdminMarqueeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/home' },
    { path: '/auth', name: 'auth', component: AuthView, meta: { public: true } },
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: 'home', name: 'home', component: HomeView, meta: { hideForAdmin: true } },
        { path: 'square', name: 'square', component: WorksSquareView, meta: { hideForAdmin: true } },
        {
          path: 'my-works',
          name: 'myWorks',
          component: MyWorksView,
          meta: { requiresAuth: true, hideForAdmin: true },
        },
        {
          path: 'my-work-comments',
          name: 'myWorkComments',
          component: MyWorkCommentsView,
          meta: { requiresAuth: true, hideForAdmin: true },
        },
        { path: 'profile', name: 'profile', component: ProfileView, meta: { requiresAuth: true } },
        { path: 'orders', name: 'orders', component: OrdersView, meta: { requiresAuth: true } },
        {
          path: 'billing-messages',
          name: 'billingMessages',
          component: BillingMessagesView,
          meta: { requiresAuth: true },
        },
        { path: 'favorites', name: 'favorites', component: FavoritesView, meta: { requiresAuth: true } },
        { path: 'my-resources', name: 'myResources', component: MyResourcesView, meta: { requiresAuth: true } },
        {
          path: 'admin-dashboard',
          name: 'adminDashboard',
          component: AdminDashboardView,
          meta: { requiresAuth: true, requiresAdmin: true },
        },
        { path: 'users', name: 'users', component: UserManagementView, meta: { requiresAdmin: true } },
        { path: 'admin-resources', name: 'adminResources', component: AdminResourcesView, meta: { requiresAdmin: true } },
        { path: 'admin-works', name: 'adminWorks', component: AdminWorksView, meta: { requiresAdmin: true } },
        {
          path: 'admin-work-comments',
          name: 'adminWorkComments',
          component: AdminWorkCommentsView,
          meta: { requiresAdmin: true },
        },
        {
          path: 'admin-marquee',
          name: 'adminMarquee',
          component: AdminMarqueeView,
          meta: { requiresAdmin: true },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/home' },
  ],
})

const ADMIN_HOME = { name: 'adminDashboard' }

router.beforeEach((to) => {
  if (to.meta?.public) return true
  if (to.meta?.requiresAuth && !isLoggedIn()) {
    return { name: 'auth', query: { redirect: to.fullPath } }
  }
  if (isAdmin() && to.matched.some((r) => r.meta?.hideForAdmin)) {
    return ADMIN_HOME
  }
  // Admin branch: remove Favorites page
  if (to.name === 'favorites' && isAdmin()) {
    return ADMIN_HOME
  }
  if (to.name === 'billingMessages' && isAdmin()) {
    return { name: 'orders' }
  }
  if (to.name === 'myResources' && isAdmin()) {
    return { name: 'adminResources' }
  }
  if (to.meta?.requiresAdmin && !isAdmin()) {
    return { name: 'home' }
  }
  return true
})

export default router
