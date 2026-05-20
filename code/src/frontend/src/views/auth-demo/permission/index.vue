<template>
  <div class="h-full">
    <n-card title="权限示例" :bordered="false" class="h-full rounded-8px shadow-sm">
      <div class="pb-12px">
        <n-gradient-text type="primary" :size="20">当前用户的权限：{{ auth.userInfo.userRole }}</n-gradient-text>
      </div>
      <div class="py-12px">
        <n-gradient-text type="primary" :size="20">权限指令 v-permission</n-gradient-text>
      </div>
      <div>
        <n-button v-permission="'admin'" class="mr-12px">admin可见</n-button>
        <n-button v-permission="'teacher'" class="mr-12px">teacher可见</n-button>
        <n-button v-permission="['admin', 'student']">admin和student可见</n-button>
      </div>
      <div class="py-12px">
        <n-gradient-text type="primary" :size="20">权限函数 hasPermission</n-gradient-text>
      </div>
      <n-space>
        <n-button v-if="hasPermission('admin')">admin可见</n-button>
        <n-button v-if="hasPermission('teacher')">teacher可见</n-button>
        <n-button v-if="hasPermission(['admin', 'student'])">admin和student可见</n-button>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/store';
import { usePermission } from '@/composables';

const auth = useAuthStore();
const { hasPermission } = usePermission();
</script>

<style scoped></style>
