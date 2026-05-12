const plugin: AuthRoute.Route = {
  name: 'plugin',
  path: '/plugin',
  component: (() => import('@/views/teacher/correct/index.vue')) as any,
  meta: {
    title: '自动批改',
    i18nTitle: 'routes.plugin',
    requiresAuth: true,
    keepAlive: true,
    singleLayout: 'basic',
    icon: 'clarity:plugin-line',
    order: 4,
    permissions: ['super', 'admin']
  }
};

export default plugin;
