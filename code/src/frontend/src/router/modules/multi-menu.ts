const multiMenu: AuthRoute.Route = {
  name: 'multi-menu',
  path: '/multi-menu',
  component: (() => import('@/views/student/correct/index.vue')) as any,
  meta: {
    title: '批改',
    i18nTitle: 'routes.multi-menu',
    requiresAuth: true,
    keepAlive: true,
    singleLayout: 'basic',
    icon: 'carbon:menu',
    order: 8,
    permissions: ['student', 'admin']
  }
};

export default multiMenu;
