const component: AuthRoute.Route = {
  name: 'component',
  path: '/component',
  component: (() => import('@/views/teacher/assesment/index.vue')) as any,
  meta: {
    title: '考核题目生成',
    i18nTitle: 'routes.component',
    requiresAuth: true,
    keepAlive: true,
    singleLayout: 'basic',
    icon: 'cib:app-store',
    order: 3,
    permissions: ['admin', 'super']
  }
};

export default component;
