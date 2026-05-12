// src/router/permission.ts

import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router';
import { routeName } from '@/router';
import { useAuthStore } from '@/store';
import { exeStrategyActions } from '@/utils'; // 移除 localStg 的导入，因为它不再直接用于登录判断
import { createDynamicRouteGuard } from './dynamic';

/** 处理路由页面的权限 */
export async function createPermissionGuard(
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) {
  // 动态路由
  const permission = await createDynamicRouteGuard(to, from, next); //
  if (!permission) return; //

  // 外链路由, 从新标签打开，返回上一个路由
  if (to.meta.href) {
    //
    window.open(to.meta.href); //
    next({ path: from.fullPath, replace: true, query: from.query }); //
    return; //
  }

  const auth = useAuthStore(); //
  // === 关键修改：直接从 sessionStorage 获取 'session_id' ===
  const isLogin = Boolean(sessionStorage.getItem('session_id')); // <-- 这一行是主要的修改
  // eslint-disable-next-line no-console
  console.log('在 permission.ts 中:', {
    isLogin,
    toPath: to.fullPath,
    toName: to.name,
    fromPath: from.fullPath,
    fromName: from.name,
    needLogin: Boolean(to.meta?.requiresAuth) || Boolean(to.meta.permissions?.length)
  });
  const permissions = to.meta.permissions || []; //
  const needLogin = Boolean(to.meta?.requiresAuth) || Boolean(permissions.length); //
  const hasPermission = !permissions.length || permissions.includes(auth.userInfo.userRole); //

  const actions: Common.StrategyAction[] = [
    // 策略 1: 已登录状态跳转登录页，跳转至首页
    [
      isLogin && to.name === routeName('login'), //
      () => {
        next({ name: routeName('root') }); //
      }
    ],
    // 策略 2: 不需要登录权限的页面直接通行
    [
      !needLogin, //
      () => {
        next(); //
      }
    ],
    // 策略 3: 未登录状态进入需要登录权限的页面
    [
      !isLogin && needLogin, //
      () => {
        const redirect = to.fullPath; //
        next({ name: routeName('login'), query: { redirect } }); //
      }
    ],
    // 策略 4: 登录状态进入需要登录权限的页面，有权限直接通行
    [
      isLogin && needLogin && hasPermission, //
      () => {
        next(); //
      }
    ],
    // 策略 5: 登录状态进入需要登录权限的页面，无权限，重定向到无权限页面
    [
      isLogin && needLogin && !hasPermission, //
      () => {
        next({ name: routeName('403') }); //
      }
    ]
  ];

  exeStrategyActions(actions); //
}
