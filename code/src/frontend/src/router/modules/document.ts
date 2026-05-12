const document: AuthRoute.Route = {
  name: 'document',
  path: '/document',
  component: (() => import('@/views/teacher/lesson-plan/index.vue')) as any,
  meta: {
    title: '教学计划生成',
    i18nTitle: 'routes.document',
    requiresAuth: true,
    keepAlive: true,
    singleLayout: 'basic',
    icon: 'mdi:file-document-multiple-outline',
    order: 2
  }
};

export default document;
