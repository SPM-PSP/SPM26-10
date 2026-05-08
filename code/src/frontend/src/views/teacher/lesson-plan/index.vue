<!-- eslint-disable vue/no-v-html -->
<template>
  <div class="h-full">
    <n-card title="教学计划生成" :bordered="false" class="rounded-8px shadow-sm">
      <div class="pb-12px text-16px">通过您的课程大纲、课程级别及预计课时，针对性输出教学计划</div>
      <n-card title="课程信息" :bordered="false" class="mt-10px rounded-8px shadow-sm">
        <n-form ref="formRef" :model="course_data" :rules="course_data_rules" size="large" :show-label="true">
          <n-form-item label="课程大纲" path="course_outline">
            <n-input v-model:value="course_data.course_outline" placeholder="请输入课程大纲" />
          </n-form-item>
          <n-form-item label="课程等级" path="course_level">
            <n-input v-model:value="course_data.course_level" placeholder="请输入课程等级，例如“大学三年级”" />
          </n-form-item>
          <n-form-item label="预计课时" path="expected_duration_hours">
            <n-select v-model:value="course_data.expected_duration_hours" :options="hours_options" filterable />
          </n-form-item>
          <n-space :vertical="true" :size="18">
            <n-button
              type="primary"
              size="large"
              :block="true"
              :round="true"
              :loading="isLoading"
              @click="handleSubmit"
            >
              {{ isLoading ? '提交中...' : '提交' }}
            </n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-space vertical class="mt-20px">
        <n-card title="教学计划" size="huge" :bordered="false" class="rounded-8px shadow-sm">
          <template v-if="lessonPlanContent">
            // eslint-disable-next-line vue/no-v-html, vue/no-v-html
            <div class="markdown-body" v-html="lessonPlanHtml"></div>
          </template>
          <template v-else>
            <n-empty description="提交课程信息后将在此处显示教学计划" />
          </template>
        </n-card>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'; // 引入 computed
import type { FormInst } from 'naive-ui';
import { marked } from 'marked'; // 引入 marked 库
import { formRules } from '@/utils';
import _axios from '@/utils/request';
import type { CourseOutlineInfo, CoursePlanApiResponse } from '@/types/document'; // 导入我们定义的类型

// 表单引用
const formRef = ref<HTMLElement & FormInst>();
// 加载状态
const isLoading = ref(false);
// 教学计划内容 (Markdown 格式)
const lessonPlanContent = ref<string | null>(null);

// 使用 computed 属性将 Markdown 转换为 HTML
const lessonPlanHtml = computed(() => {
  if (lessonPlanContent.value) {
    // marked.parse() 将 Markdown 字符串转换为 HTML 字符串
    return marked.parse(lessonPlanContent.value);
  }
  return ''; // 如果没有内容，返回空字符串
});

// 表单数据
const course_data = reactive<CourseOutlineInfo>({
  course_outline: '',
  course_level: '',
  expected_duration_hours: null
});

// 课时选项
const hours_options = Array.from({ length: 99 }, (_, i) => ({
  label: `${i + 1}课时`,
  value: i + 1
}));

// 表单验证规则
const course_data_rules = {
  course_outline: formRules.course_outline,
  course_level: formRules.course_level,
  expected_duration_hours: formRules.expected_duration_hours
};

// 提交处理函数
const handleSubmit = async () => {
  try {
    isLoading.value = true;
    await formRef.value?.validate();

    const requestPayload: CourseOutlineInfo = {
      course_outline: course_data.course_outline,
      course_level: course_data.course_level,
      expected_duration_hours:
        typeof course_data.expected_duration_hours === 'number' ? course_data.expected_duration_hours : 0
    };

    const response = await _axios.post<CoursePlanApiResponse>('/api/teacher/lesson_plan/generate', requestPayload);

    if (response.data.status === 'success') {
      window.$message?.success('教学计划生成成功！');
      lessonPlanContent.value = response.data.lesson_plan; // 赋值 Markdown 字符串
    } else {
      window.$message?.error(response.data.lesson_plan || '教学计划生成失败！');
      lessonPlanContent.value = null;
    }
  } catch (errors) {
    window.$message?.error('请检查表单填写或网络状况');
    lessonPlanContent.value = null;
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
/* 这是一个基础的 Markdown 样式，以让渲染出来的 HTML 有更好的可读性 */
/* 您可以根据需要进行调整和美化 */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: bold;
}

.markdown-body :deep(p) {
  margin-bottom: 0.8em;
  line-height: 1.6;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-left: 20px;
  margin-bottom: 0.8em;
}

.markdown-body :deep(li) {
  margin-bottom: 0.4em;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1em;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.markdown-body :deep(th) {
  background-color: #f2f2f2;
}

/* 调整卡片内容垂直间距，如果需要 */
.n-card__content.n-card__content {
  padding-bottom: 16px;
}

.mt-20px {
  margin-top: 20px;
}
</style>
