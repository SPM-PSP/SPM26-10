<template>
  <div class="h-full">
    <n-space vertical :size="20">
      <n-card
        :bordered="false"
        :class="['rounded-8px shadow-sm hero-card', theme.darkMode ? 'hero-card--dark' : 'hero-card--light']"
      >
        <n-space vertical :size="12">
          <n-tag type="error" round>管理工作台</n-tag>
          <div class="text-28px font-700">欢迎回来，{{ auth.userInfo.userName }}</div>
          <div :class="['text-15px hero-card__subtitle', theme.darkMode ? 'hero-card__subtitle--dark' : 'hero-card__subtitle--light']">
            管理员首页聚合系统概览、用户管理、资源管理，并保留跨角色入口用于联调和演示。
          </div>
        </n-space>
      </n-card>

      <n-grid cols="1 s:2 l:3" responsive="screen" :x-gap="16" :y-gap="16">
        <n-grid-item v-for="item in adminActions" :key="item.title">
          <n-card :bordered="false" class="rounded-8px shadow-sm action-card" hoverable @click="go(item.routeName)">
            <n-space vertical :size="10">
              <div class="text-18px font-600">{{ item.title }}</div>
              <div class="text-14px text-#64748b">{{ item.description }}</div>
            </n-space>
          </n-card>
        </n-grid-item>
      </n-grid>

      <n-card title="跨角色入口" :bordered="false" class="rounded-8px shadow-sm">
        <n-grid cols="1 s:2 l:3" responsive="screen" :x-gap="16" :y-gap="16">
          <n-grid-item v-for="item in crossRoleActions" :key="item.title">
            <n-button secondary block strong @click="go(item.routeName)">
              {{ item.title }}
            </n-button>
          </n-grid-item>
        </n-grid>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useAuthStore, useThemeStore } from '@/store';

defineOptions({ name: 'AdminHomePage' });

const router = useRouter();
const auth = useAuthStore();
const theme = useThemeStore();

const adminActions = [
  {
    title: '数据概览',
    description: '查看系统核心指标、活跃情况和教学建议。',
    routeName: 'dashboard_analysis'
  },
  {
    title: '用户管理',
    description: '创建账户并查看教师、学生和管理员列表。',
    routeName: 'admin_user_management'
  },
  {
    title: '资源管理',
    description: '查看当前系统生成的教案、考核和练习资源。',
    routeName: 'admin_resource_management'
  },
  {
    title: '在线问答',
    description: '以管理员身份验证公共问答链路是否可用。',
    routeName: 'admin_online_ask'
  }
];

const crossRoleActions = [
  { title: '进入学生首页', routeName: 'student_home' },
  { title: '进入教师首页', routeName: 'teacher_home' },
  { title: '进入学生问答', routeName: 'student_online_ask' }
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
    radial-gradient(circle at top right, rgb(251 113 133 / 28%), transparent 38%),
    linear-gradient(135deg, rgb(255 245 245 / 98%), rgb(255 247 237 / 96%));
  border: 1px solid rgb(254 205 211 / 86%);
}

.hero-card--dark {
  background:
    radial-gradient(circle at top right, rgb(244 63 94 / 16%), transparent 35%),
    linear-gradient(135deg, rgb(35 14 23 / 96%), rgb(31 22 34 / 94%));
  border: 1px solid rgb(251 113 133 / 18%);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 3%),
    0 20px 50px rgb(2 6 23 / 34%);
}

.hero-card__subtitle--light {
  color: #57534e;
}

.hero-card__subtitle--dark {
  color: #c0aab7;
}

.action-card {
  min-height: 180px;
}
</style>
