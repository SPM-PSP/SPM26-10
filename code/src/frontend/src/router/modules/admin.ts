const admin: AuthRoute.Route = {
  name: 'admin',
  path: '/admin',
  component: 'basic',
  children: [
    {
      name: 'admin_home',
      path: '/admin/home',
      component: 'self',
      meta: {
        title: '管理首页',
        requiresAuth: true,
        icon: 'mdi:home-outline',
        permissions: ['admin']
      }
    },
    {
      name: 'dashboard_analysis',
      path: '/dashboard/analysis',
      component: 'self',
      meta: {
        title: '数据概览',
        requiresAuth: true,
        icon: 'icon-park-outline:analysis',
        permissions: ['admin']
      }
    },
    {
      name: 'admin_online_ask',
      path: '/admin/online/ask',
      component: 'self',
      meta: {
        title: '在线问答',
        requiresAuth: true,
        icon: 'mdi:chat-processing-outline',
        permissions: ['admin']
      }
    },
    {
      name: 'admin_user_management',
      path: '/admin/user/management',
      component: 'self',
      meta: {
        title: '用户管理',
        requiresAuth: true,
        icon: 'ic:round-manage-accounts',
        permissions: ['admin']
      }
    },
    {
      name: 'admin_resource_management',
      path: '/admin/resource/management',
      component: 'self',
      meta: {
        title: '资源管理',
        requiresAuth: true,
        icon: 'fluent:book-information-24-regular',
        permissions: ['admin']
      }
    }
  ],
  meta: {
    title: '管理工作台',
    icon: 'mdi:shield-crown-outline',
    order: 3,
    permissions: ['admin']
  }
};

export default admin;
