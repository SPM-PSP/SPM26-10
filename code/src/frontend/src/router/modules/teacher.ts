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
      name: 'teacher_classes',
      path: '/teacher/classes',
      component: 'self',
      meta: {
        title: '班级管理',
        requiresAuth: true,
        icon: 'mdi:account-school-outline',
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
      name: 'teacher_papers',
      path: '/teacher/papers',
      component: 'self',
      meta: {
        title: '试卷生成与发布',
        requiresAuth: true,
        icon: 'mdi:file-document-multiple-outline',
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
      name: 'teacher_paper_results',
      path: '/teacher/paper/results',
      component: 'self',
      meta: {
        title: '试卷结果分析',
        requiresAuth: true,
        icon: 'mdi:chart-box-outline',
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
