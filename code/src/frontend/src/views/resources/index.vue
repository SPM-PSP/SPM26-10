<template>
  <div class="h-full">
    <n-card title="资源导出" :bordered="false" class="rounded-8px shadow-sm">
      <n-space vertical :size="18">
        <div class="text-15px text-#64748b">
          这个页面暂时保留为资源查看入口。当前系统已经把“资源管理”统一收口到管理员端，导出链路后续再接入。
        </div>
        <n-alert type="info" title="当前状态">
          资源导出功能未作为本轮角色统一改造的主路径实现。请使用“管理员 > 资源管理”查看现有教案、考核和练习资源。
        </n-alert>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'ResourcesPage' });
</script>
