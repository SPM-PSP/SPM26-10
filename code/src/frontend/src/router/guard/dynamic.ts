// src/router/dynamic.ts

import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router';
import { routeName } from '@/router';
import { useRouteStore } from '@/store';
// import { localStg } from '@/utils'; // 由于不再使用 localStg 判断登录状态，这个导入可以移除，但保留也无妨

/**
 * 动态路由
 */
export async function createDynamicRouteGuard(
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext
) {
  const route = useRouteStore();

  // === 关键修改：直接从 sessionStorage 获取 'session_id' ===
  // 这行代码将解决“类型“"session_id"”的参数不能赋给类型“keyof Local”的参数。”的错误
  const isLogin = Boolean(sessionStorage.getItem('session_id'));
  // =======================================================

  // 初始化权限路由
  if (!route.isInitAuthRoute) {
    // 未登录情况下直接回到登录页，登录成功后再加载权限路由
    if (!isLogin) {
      const toName = to.name as AuthRoute.AllRouteKey;
      // 如果目标路由是有效的常量路由且不需要认证（例如登录页本身），则放行
      if (route.isValidConstantRoute(toName) && !to.meta.requiresAuth) {
        next();
      } else {
        // 否则，重定向到登录页，并带上当前完整路径作为重定向参数
        const redirect = to.fullPath;
        next({ name: routeName('login'), query: { redirect } });
      }
      return false; // 阻止后续守卫的执行，因为已经处理了导航
    }

    // 已登录且路由未初始化，则初始化权限路由
    await route.initAuthRoute();

    // 如果初始化后发现当前目标路由是404（意味着之前因为动态路由未加载而被捕获）
    if (to.name === routeName('not-found')) {
      // 若路由是从根路由重定向过来的，重新回到根路由
      const ROOT_ROUTE_NAME: AuthRoute.AllRouteKey = 'root';
      const path = to.redirectedFrom?.name === ROOT_ROUTE_NAME ? '/' : to.fullPath;
      // 重定向回正确的路径
      next({ path, replace: true, query: to.query, hash: to.hash });
      return false; // 阻止后续守卫的执行
    }
  }

  // 权限路由已经加载，但仍然未找到匹配的路由，重定向到404页面
  if (to.name === routeName('not-found')) {
    next({ name: routeName('404'), replace: true });
    return false; // 阻止后续守卫的执行
  }

  return true; // 允许导航继续进行到下一个守卫或最终路由
}
