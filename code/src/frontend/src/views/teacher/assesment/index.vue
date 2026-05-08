<!-- eslint-disable vue/no-v-html -->
<template>
  <div class="h-full">
    <n-card title="考核题目生成" :bordered="false" class="rounded-8px shadow-sm">
      <div class="pb-12px text-16px">设置考察内容、题目类型与难度，智能生成考核题目</div>
      <n-card title="课程信息" :bordered="false" class="mt-10px rounded-8px shadow-sm">
        <n-form ref="formRef" :model="assesment" :rules="assessment_rules" size="large" :show-label="true">
          <n-form-item label="考察内容" path="topic">
            <n-input v-model:value="assesment.topic" placeholder="请输入考察内容" />
          </n-form-item>
          <n-form-item label="题型" path="question_type">
            <n-select v-model:value="assesment.question_type" :options="question_type_options" />
          </n-form-item>
          <n-form-item label="难度" path="difficulty_level">
            <n-select v-model:value="assesment.difficulty_level" :options="difficulty_level_options" />
          </n-form-item>
          <n-form-item label="题目数量" path="num_questions">
            <n-select v-model:value="assesment.num_questions" :options="num_questions_options" filterable />
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
        <n-card title="考核题目" size="huge" :bordered="false" class="rounded-8px shadow-sm">
          <template v-if="assessmentContent">
            <div class="markdown-body" v-html="assessmentHtml"></div>
          </template>
          <template v-else>
            <n-empty description="提交课程信息后将在此处显示考核题目" />
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
import _axios from '@/utils/request'; // 引入封装的 axios 实例
import type { AssessmentRequestPayload, AssessmentApiResponse } from '@/types/assessment'; // 导入我们定义的类型

// 表单引用
const formRef = ref<HTMLElement & FormInst>();
// 加载状态
const isLoading = ref(false);
// 考核题目内容 (Markdown 格式)
const assessmentContent = ref<string | null>(null);

// 使用 computed 属性将 Markdown 转换为 HTML
const assessmentHtml = computed(() => {
  if (assessmentContent.value) {
    // marked.parse() 将 Markdown 字符串转换为 HTML 字符串
    return marked.parse(assessmentContent.value);
  }
  return ''; // 如果没有内容，返回空字符串
});

// 表单数据
const assesment = reactive<AssessmentRequestPayload>({
  topic: '',
  question_type: null,
  difficulty_level: null,
  num_questions: null
});

const question_type_options = [
  { label: '选择题', value: '选择题' },
  { label: '填空题', value: '填空题' },
  { label: '简答题', value: '简答题' },
  { label: '编程题', value: '编程题' }
];

const difficulty_level_options = [
  { label: '简单', value: '简单' },
  { label: '中等', value: '中等' },
  { label: '困难', value: '困难' }
];

// 注意：题目数量的 options 之前是“课时”，这里改成“题目数量”
const num_questions_options = Array.from({ length: 50 }, (_, i) => ({
  // 假设最多生成50道题
  label: `${i + 1}题`,
  value: i + 1
}));

// 表单验证规则 (您需要确保 formRules 中有 topic, question_type, difficulty_level, num_questions 的规则)
const assessment_rules = {
  // 更改为 assessment_rules，与表单绑定
  topic: formRules.topic,
  question_type: formRules.question_type,
  difficulty_level: formRules.difficulty_level,
  num_questions: formRules.num_questions
};

// 提交处理函数
const handleSubmit = async () => {
  try {
    isLoading.value = true;
    // 1. 表单验证
    await formRef.value?.validate();

    // 2. 构造请求体数据，并处理可能为 null 的字段
    const requestPayload: AssessmentRequestPayload = {
      topic: assesment.topic,
      question_type: assesment.question_type || '', // 如果为 null，发送空字符串或根据后端要求
      difficulty_level: assesment.difficulty_level || '', // 如果为 null，发送空字符串或根据后端要求
      num_questions: assesment.num_questions || 0 // 如果为 null，发送 0 或根据后端要求
    };

    // 3. 调用接口
    const response = await _axios.post<AssessmentApiResponse>('/api/teacher/assessment/generate', requestPayload);

    // 4. 处理接口响应
    if (response.data.status === 'success') {
      window.$message?.success('考核题目生成成功！');
      assessmentContent.value = response.data.assessment_content; // 更新考核题目内容
      // eslint-disable-next-line no-console
      console.log('生成的考核题目 (Markdown):', assessmentContent.value);
    } else {
      window.$message?.error(response.data.assessment_content || '考核题目生成失败！');
      assessmentContent.value = null; // 清空旧内容
    }
  } catch (errors) {
    window.$message?.error('请检查表单填写或网络状况');
    assessmentContent.value = null; // 清空旧内容
  } finally {
    isLoading.value = false; // 无论成功失败都关闭加载状态
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
