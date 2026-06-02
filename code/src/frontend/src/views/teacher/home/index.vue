<template>
  <div class="h-full">
    <n-space vertical :size="20">
      <n-card
        :bordered="false"
        :class="['rounded-8px shadow-sm hero-card', theme.darkMode ? 'hero-card--dark' : 'hero-card--light']"
      >
        <n-space vertical :size="12">
          <n-tag type="info" round>教师工作台</n-tag>
          <div class="text-28px font-700">欢迎回来，{{ auth.userInfo.userName }}</div>
          <div :class="['text-15px hero-card__subtitle', theme.darkMode ? 'hero-card__subtitle--dark' : 'hero-card__subtitle--light']">
            当前教师端收口到备课、出题、问答和批改四类主流程，便于直接演示。
          </div>
        </n-space>
      </n-card>

      <n-grid cols="1 s:2 l:4" responsive="screen" :x-gap="16" :y-gap="16">
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

defineOptions({ name: 'TeacherHomePage' });

const router = useRouter();
const auth = useAuthStore();
const theme = useThemeStore();

const actions = [
  {
    title: '班级管理',
    description: '创建班级、查看班级码，并追踪学生加入情况。',
    routeName: 'teacher_classes'
  },
  {
    title: '在线问答',
    description: '快速查询课程知识点，作为备课和答疑的辅助入口。',
    routeName: 'teacher_online_ask'
  },
  {
    title: '教学计划生成',
    description: '根据课程大纲、课时和年级生成结构化教学计划。',
    routeName: 'teacher_lesson-plan'
  },
  {
    title: '考核题目生成',
    description: '按知识点、题型与难度自动生成考核内容。',
    routeName: 'teacher_assesment'
  },
  {
    title: '试卷生成与发布',
    description: '从教学计划生成试卷草稿，编辑后直接发布到班级。',
    routeName: 'teacher_papers'
  },
  {
    title: '作业批改',
    description: '录入题目、学生答案与参考答案，获取自动反馈。',
    routeName: 'teacher_correct'
  },
  {
    title: '试卷结果分析',
    description: '查看学生交卷情况、逐题反馈和整体正确率。',
    routeName: 'teacher_paper_results'
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
    radial-gradient(circle at top right, rgb(96 165 250 / 28%), transparent 38%),
    linear-gradient(135deg, rgb(241 248 255 / 98%), rgb(238 242 255 / 96%));
  border: 1px solid rgb(191 219 254 / 86%);
}

.hero-card--dark {
  background:
    radial-gradient(circle at top right, rgb(59 130 246 / 18%), transparent 35%),
    linear-gradient(135deg, rgb(11 22 40 / 96%), rgb(20 24 44 / 94%));
  border: 1px solid rgb(96 165 250 / 22%);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 3%),
    0 20px 50px rgb(2 6 23 / 32%);
}

.hero-card__subtitle--light {
  color: #475569;
}

.hero-card__subtitle--dark {
  color: #a4b1c9;
}

.action-card {
  min-height: 180px;
}
</style>
