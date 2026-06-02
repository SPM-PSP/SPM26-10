<template>
  <div class="h-full">
    <n-space vertical :size="20">
      <n-card
        :bordered="false"
        :class="['rounded-8px shadow-sm hero-card', theme.darkMode ? 'hero-card--dark' : 'hero-card--light']"
      >
        <n-space vertical :size="12">
          <n-tag type="success" round>学生工作台</n-tag>
          <div class="text-28px font-700">欢迎回来，{{ auth.userInfo.userName }}</div>
          <div :class="['text-15px hero-card__subtitle', theme.darkMode ? 'hero-card__subtitle--dark' : 'hero-card__subtitle--light']">
            从提问、随练到纠错，当前页面保留的是已经接通后端的学生功能。
          </div>
        </n-space>
      </n-card>

      <n-grid cols="1 s:2 l:3" responsive="screen" :x-gap="16" :y-gap="16">
        <n-grid-item v-for="item in actions" :key="item.title">
          <n-card :bordered="false" class="rounded-8px shadow-sm action-card" hoverable @click="go(item.routeName)">
            <n-space vertical :size="10">
              <div class="text-18px font-600">{{ item.title }}</div>
              <div class="text-14px text-#64748b">{{ item.description }}</div>
            </n-space>
          </n-card>
        </n-grid-item>
      </n-grid>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useAuthStore, useThemeStore } from '@/store';

defineOptions({ name: 'StudentHomePage' });

const router = useRouter();
const auth = useAuthStore();
const theme = useThemeStore();

const actions = [
  {
    title: '我的班级',
    description: '输入班级码加入教师创建的班级，并管理自己的课程入口。',
    routeName: 'student_classes'
  },
  {
    title: '班级试卷',
    description: '查看教师发布到班级的试卷，完成作答并接收即时批改。',
    routeName: 'student_papers'
  },
  {
    title: '在线问答',
    description: '基于课程知识库提问，边生成边显示回答。',
    routeName: 'student_online_ask'
  },
  {
    title: '练习生成',
    description: '按知识点生成练习题，支持不同题型和数量。',
    routeName: 'student_practice_question_generation'
  },
  {
    title: '练习纠错',
    description: '提交自己的答案，获取反馈、错误定位和修正建议。',
    routeName: 'student_correct'
  }
];

function go(routeName: string) {
  router.push({ name: routeName as AuthRoute.AllRouteKey });
}
</script>

<style scoped>
.hero-card {
  transition:
    background 0.25s ease,
    box-shadow 0.25s ease,
    border-color 0.25s ease;
}

.hero-card--light {
  background:
    radial-gradient(circle at top right, rgb(110 231 183 / 30%), transparent 36%),
    linear-gradient(135deg, rgb(244 253 248 / 98%), rgb(239 246 255 / 96%));
  border: 1px solid rgb(209 250 229 / 88%);
}

.hero-card--dark {
  background:
    radial-gradient(circle at top right, rgb(16 185 129 / 16%), transparent 34%),
    linear-gradient(135deg, rgb(7 21 22 / 96%), rgb(16 24 39 / 94%));
  border: 1px solid rgb(52 211 153 / 20%);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 3%),
    0 20px 50px rgb(2 6 23 / 32%);
}

.hero-card__subtitle--light {
  color: #4b5563;
}

.hero-card__subtitle--dark {
  color: #9fb0c7;
}

.action-card {
  min-height: 170px;
}
</style>
