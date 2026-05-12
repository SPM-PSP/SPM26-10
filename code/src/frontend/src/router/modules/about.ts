const about: AuthRoute.Route = {
  name: 'about',
  path: '/about',
  component: (() => import('@/views/resources/index.vue')) as any,
  meta: {
    title: '资源导出',
    i18nTitle: 'routes.about',
    requiresAuth: true,
    keepAlive: true,
    singleLayout: 'basic',
    permissions: [],
    icon: 'fluent:book-information-24-regular',
    order: 10
  }
};

export default about;
