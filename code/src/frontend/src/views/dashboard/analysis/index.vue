<!-- eslint-disable no-console -->
<!-- eslint-disable no-console -->
<template>
  <div class="h-full">
    <n-card title="仪表盘概览" :bordered="false" class="rounded-8px shadow-sm">
      <n-space :vertical="true" :size="24">
        <n-card title="核心指标" :bordered="false" class="rounded-8px shadow-sm">
          <n-grid cols="1 s:2 m:4" responsive="screen" :x-gap="16" :y-gap="16">
            <n-grid-item>
              <n-statistic label="总教师数" :value="metrics.total_teachers" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="总学生数" :value="metrics.total_students" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="总课程数" :value="metrics.total_courses" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="今日活跃教师" :value="metrics.active_teachers_today" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="今日活跃学生" :value="metrics.active_students_today" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="本周活跃教师" :value="metrics.active_teachers_week" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="本周活跃学生" :value="metrics.active_students_week" />
            </n-grid-item>
          </n-grid>
        </n-card>

        <n-card title="效率与表现" :bordered="false" class="rounded-8px shadow-sm">
          <n-grid cols="1 s:2 m:3" responsive="screen" :x-gap="16" :y-gap="16">
            <n-grid-item>
              <n-statistic label="平均备课时长 (小时)" :value="metrics.avg_prep_time_hours" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="平均批改时长 (分钟)" :value="metrics.avg_correction_time_minutes" />
            </n-grid-item>
            <n-grid-item>
              <n-statistic label="平均学生准确率" :value="metrics.avg_student_accuracy * 100 + '%'" />
            </n-grid-item>
          </n-grid>
        </n-card>

        <n-card title="洞察与建议" :bordered="false" class="rounded-8px shadow-sm">
          <n-grid cols="1 m:2" responsive="screen" :x-gap="16" :y-gap="16">
            <n-grid-item>
              <n-h3>常见错误</n-h3>
              <n-list bordered>
                <n-list-item v-for="(error, index) in metrics.top_common_errors" :key="index">
                  {{ error }}
                </n-list-item>
                <n-empty
                  v-if="metrics.top_common_errors && metrics.top_common_errors.length === 0"
                  description="暂无常见错误数据"
                />
              </n-list>
            </n-grid-item>
            <n-grid-item>
              <n-h3>课程优化建议</n-h3>
              <n-list bordered>
                <n-list-item v-for="(suggestion, index) in metrics.course_optimization_suggestions" :key="index">
                  {{ suggestion }}
                </n-list-item>
                <n-empty
                  v-if="metrics.course_optimization_suggestions && metrics.course_optimization_suggestions.length === 0"
                  description="暂无课程优化建议"
                />
              </n-list>
            </n-grid-item>
          </n-grid>
        </n-card>

        <n-alert v-if="errorMsg" type="error" title="数据加载失败">
          {{ errorMsg }}
        </n-alert>
      </n-space>
    </n-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'; // 移除 watch, computed
import _axios from '@/utils/request';
import type { DashboardMetricsResponse } from '@/types/dashboard';

// loading 变量依然保留，但因为 n-spin 移除，它的作用只是控制 errorMsg 等逻辑
const loading = ref(true);
const errorMsg = ref<string | null>(null);

// spinClasses 已移除，因为 n-spin 组件不再需要它
// const spinClasses = computed(() => { ... });

const metrics = ref<DashboardMetricsResponse>({
  total_teachers: 0,
  total_students: 0,
  total_courses: 0,
  avg_prep_time_hours: 0,
  avg_correction_time_minutes: 0,
  avg_student_accuracy: 0,
  top_common_errors: [],
  active_teachers_today: 0,
  active_students_today: 0,
  active_teachers_week: 0,
  active_students_week: 0,
  course_optimization_suggestions: []
});

// watch(loading, newVal => { ... }); // 移除 watch 监听

/**
 * 获取仪表盘指标数据
 */
async function fetchDashboardMetrics() {
  loading.value = true;
  errorMsg.value = null;
  // eslint-disable-next-line no-console
  console.log('FETCHING: Initiating request, loading =', loading.value);

  try {
    const response = await _axios.get<DashboardMetricsResponse>('/api/admin/dashboard/metrics');

    // eslint-disable-next-line no-console
    console.log('FETCHING: API Response received (data):', response.data);

    metrics.value = response.data;
    // eslint-disable-next-line no-console
    console.log('FETCHING: Metrics value updated, metrics.value:', metrics.value);

    // 防御性编程：确保数组字段即使后端返回 null 也能被处理为 []
    if (!metrics.value.top_common_errors) {
      metrics.value.top_common_errors = [];
    }
    if (!metrics.value.course_optimization_suggestions) {
      metrics.value.course_optimization_suggestions = [];
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('FETCHING: Failed to fetch dashboard metrics:', error);
    errorMsg.value = '无法加载仪表盘数据。请检查网络或稍后再试。';
    window.$message?.error('仪表盘数据加载失败！');
  } finally {
    // eslint-disable-next-line require-atomic-updates
    loading.value = false; // 仍然设置为 false，即使没有 n-spin 也可以用于其他条件渲染
    // eslint-disable-next-line no-console
    console.log('FETCHING: FINALLY block executed, loading =', loading.value);
  }
}

// 在组件挂载后立即获取数据，确保只调用一次 (在SPA路由跳转下)
onMounted(() => {
  // eslint-disable-next-line no-console
  console.log('ONMOUNTED: Component mounted, calling fetchDashboardMetrics.');
  fetchDashboardMetrics();
});
</script>

<style scoped>
.n-card {
  margin-bottom: 16px;
}
/* 所有与 n-spin 相关的样式类都已移除，因为 n-spin 组件已删除 */
/* .relative {
  position: relative;
}
.absolute {
  position: absolute;
}
.inset-0 {
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
}
.flex {
  display: flex;
}
.items-center {
  align-items: center;
}
.justify-center {
  justify-content: center;
}
.bg-white {
  background-color: white;
}
.bg-opacity-70 {
  background-color: rgba(255, 255, 255, 0.7);
}
.z-10 {
  z-index: 10;
} */
</style>
