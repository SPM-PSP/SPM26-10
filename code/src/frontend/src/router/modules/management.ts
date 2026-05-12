const management: AuthRoute.Route = {
  name: 'management',
  path: '/management',
  component: 'basic',
  children: [
    {
      name: 'management_auth',
      path: '/management/auth',
      component: 'self',
      meta: {
        title: '获取账户列表',
        i18nTitle: 'routes.management.auth',
        requiresAuth: true,
        keepAlive: true,
        icon: 'ic:baseline-security'
      }
    },
    {
      name: 'management_role',
      path: '/management/role',
      component: 'self',
      meta: {
        title: '获取教师资源',
        i18nTitle: 'routes.management.role',
        requiresAuth: true,
        keepAlive: true,
        icon: 'carbon:user-role'
      }
    },
    {
      name: 'management_user',
      path: '/management/user',
      component: 'self',
      meta: {
        title: '导出课件',
        i18nTitle: 'routes.management.user',
        requiresAuth: true,
        keepAlive: true,
        icon: 'ic:round-manage-accounts'
      }
    },
    {
      name: 'management_route',
      path: '/management/route',
      component: 'self',
      meta: {
        title: '路由管理',
        i18nTitle: 'routes.management.route',
        requiresAuth: true,
        keepAlive: true,
        icon: 'material-symbols:route',
        permissions: ['admin']
      }
    }
  ],
  meta: {
    title: '系统管理',
    i18nTitle: 'routes.management._value',
    icon: 'carbon:cloud-service-management',
    order: 9
  }
};

export default management;
