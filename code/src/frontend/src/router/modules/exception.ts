const exception: AuthRoute.Route = {
  name: 'exception',
  path: '/exception',
  component: (() => import('@/views/student/practice_question_generation/index.vue')) as any,
  meta: {
    i18nTitle: 'routes.exception',
    title: '练习题目生成',
    requiresAuth: true,
    keepAlive: true,
    singleLayout: 'basic',
    icon: 'ant-design:exception-outlined',
    order: 7,
    permissions: ['student', 'admin']
  }
};

export default exception;
