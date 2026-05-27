/**
 * 未登录时跳转登录/注册页，登录成功后回到 redirect 路径。
 * @param {import('vue-router').Router} router
 * @param {string} [redirectPath] 默认当前页 fullPath
 */
export function goLogin(router, redirectPath) {
  const path =
    typeof redirectPath === 'string' && redirectPath
      ? redirectPath
      : router.currentRoute.value?.fullPath || '/home'
  router.push({ name: 'auth', query: { redirect: path } })
}
