const student: AuthRoute.Route = {
  name: 'student',
  path: '/student',
  component: 'basic',
  children: [
    {
      name: 'student_home',
      path: '/student/home',
      component: 'self',
      meta: {
        title: '学生首页',
        requiresAuth: true,
        icon: 'mdi:home-outline',
        permissions: ['student', 'admin']
      }
    },
    {
      name: 'student_online_ask',
      path: '/student/online/ask',
      component: 'self',
      meta: {
        title: '在线问答',
        requiresAuth: true,
        icon: 'mdi:chat-processing-outline',
        permissions: ['student', 'admin']
      }
    },
    {
      name: 'student_practice_question_generation',
      path: '/student/practice/question/generation',
      component: 'self',
      meta: {
        title: '练习生成',
        requiresAuth: true,
        icon: 'mdi:file-document-edit-outline',
        permissions: ['student', 'admin']
      }
    },
    {
      name: 'student_correct',
      path: '/student/correct',
      component: 'self',
      meta: {
        title: '练习纠错',
        requiresAuth: true,
        icon: 'mdi:clipboard-check-outline',
        permissions: ['student', 'admin']
      }
    }
  ],
  meta: {
    title: '学生工作台',
    icon: 'mdi:school-outline',
    order: 1,
    permissions: ['student', 'admin']
  }
};

export default student;
