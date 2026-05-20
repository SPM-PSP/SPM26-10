const teacher: AuthRoute.Route = {
  name: 'teacher',
  path: '/teacher',
  component: 'basic',
  children: [
    {
      name: 'teacher_home',
      path: '/teacher/home',
      component: 'self',
      meta: {
        title: '教师首页',
        requiresAuth: true,
        icon: 'mdi:home-outline',
        permissions: ['teacher', 'admin']
      }
    },
    {
      name: 'teacher_online_ask',
      path: '/teacher/online/ask',
      component: 'self',
      meta: {
        title: '在线问答',
        requiresAuth: true,
        icon: 'mdi:chat-processing-outline',
        permissions: ['teacher', 'admin']
      }
    },
    {
      name: 'teacher_lesson-plan',
      path: '/teacher/lesson-plan',
      component: 'self',
      meta: {
        title: '教学计划生成',
        requiresAuth: true,
        icon: 'mdi:book-open-page-variant-outline',
        permissions: ['teacher', 'admin']
      }
    },
    {
      name: 'teacher_assesment',
      path: '/teacher/assesment',
      component: 'self',
      meta: {
        title: '考核题目生成',
        requiresAuth: true,
        icon: 'mdi:file-document-multiple-outline',
        permissions: ['teacher', 'admin']
      }
    },
    {
      name: 'teacher_correct',
      path: '/teacher/correct',
      component: 'self',
      meta: {
        title: '作业批改',
        requiresAuth: true,
        icon: 'mdi:text-box-check-outline',
        permissions: ['teacher', 'admin']
      }
    }
  ],
  meta: {
    title: '教师工作台',
    icon: 'mdi:teach',
    order: 2,
    permissions: ['teacher', 'admin']
  }
};

export default teacher;
