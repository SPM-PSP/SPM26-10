const functionRoute: AuthRoute.Route = {
  name: 'function',
  path: '/function',
  component: (() => import('@/views/student/online_ask/index.vue')) as any,
  meta: {
    title: '在线问答',
    i18nTitle: 'routes.function',
    requiresAuth: true,
    keepAlive: true,
    singleLayout: 'basic',
    icon: 'icon-park-outline:all-application',
    order: 6,
    permissions: ['student', 'teacher', 'admin']
  }
};

export default functionRoute;
