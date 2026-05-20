<!-- eslint-disable vue/no-v-html -->
<template>
  <div class="h-full">
    <n-card title="练习生成" :bordered="false" class="rounded-8px shadow-sm">
      <div class="pb-12px text-16px">按知识点、题型和数量生成练习，结果会直接保存为你的个人练习资源。</div>

      <n-card title="练习参数" :bordered="false" class="mt-10px rounded-8px shadow-sm">
        <n-form ref="formRef" :model="formModel" :rules="rules" size="large" label-placement="left">
          <n-form-item label="知识点" path="topic_focus">
            <n-input
              v-model:value="formModel.topic_focus"
              placeholder="例如：进程通信、设备驱动、文件系统"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
            />
          </n-form-item>
          <n-form-item label="题型" path="question_type">
            <n-select v-model:value="formModel.question_type" :options="questionTypeOptions" />
          </n-form-item>
          <n-form-item label="题目数量" path="num_questions">
            <n-select v-model:value="formModel.num_questions" :options="numQuestionOptions" />
          </n-form-item>
          <n-button type="primary" size="large" :loading="isLoading" block round @click="handleSubmit">
            {{ isLoading ? '生成中...' : '生成练习' }}
          </n-button>
        </n-form>
      </n-card>

      <n-space vertical class="mt-20px">
        <n-card title="练习结果" size="huge" :bordered="false" class="rounded-8px shadow-sm">
          <template v-if="generatedContent">
            <div class="markdown-body" v-html="generatedHtml"></div>
          </template>
          <template v-else>
            <n-empty description="生成完成后，这里会显示练习题和参考答案。" />
          </template>
        </n-card>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import type { FormInst, FormRules } from 'naive-ui';
import { marked } from 'marked';
import { useAuthStore } from '@/store';
import { formRules } from '@/utils';
import _axios from '@/utils/request';

defineOptions({ name: 'StudentPracticeGenerationPage' });

interface PracticeFormModel {
  topic_focus: string;
  question_type: '选择题' | '填空题' | '简答题' | '编程题' | '混合';
  num_questions: number;
}

interface PracticeResponse {
  status: string;
  practice_questions: string;
  generated_at: string;
  resource_id: string;
}

const auth = useAuthStore();
const formRef = ref<FormInst | null>(null);
const isLoading = ref(false);
const generatedContent = ref('');

const formModel = reactive<PracticeFormModel>({
  topic_focus: '',
  question_type: '混合',
  num_questions: 3
});

const generatedHtml = computed(() => marked.parse(generatedContent.value || ''));

const questionTypeOptions = [
  { label: '混合', value: '混合' },
  { label: '选择题', value: '选择题' },
  { label: '填空题', value: '填空题' },
  { label: '简答题', value: '简答题' },
  { label: '编程题', value: '编程题' }
];

const numQuestionOptions = Array.from({ length: 5 }, (_, index) => ({
  label: `${index + 1} 题`,
  value: index + 1
}));

const rules: FormRules = {
  topic_focus: formRules.topic,
  question_type: formRules.question_type,
  num_questions: formRules.num_questions
};

async function handleSubmit() {
  try {
    await formRef.value?.validate();
    isLoading.value = true;
    generatedContent.value = '';

    const response = await _axios.post<PracticeResponse>('/api/student/practice/generate', {
      student_id: Number(auth.userInfo.userId),
      topic_focus: formModel.topic_focus,
      question_type: formModel.question_type,
      num_questions: formModel.num_questions
    });

    if (response.data.status !== 'success') {
      throw new Error('练习生成失败');
    }

    generatedContent.value = response.data.practice_questions;
    window.$message?.success('练习生成成功');
  } catch (error: any) {
    console.error('生成练习失败:', error);
    window.$message?.error(error?.response?.data?.detail || error?.message || '练习生成失败');
  } finally {
    isLoading.value = false;
  }
}
</script>

<style scoped>
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 700;
}

.markdown-body :deep(p) {
  margin-bottom: 0.8em;
  line-height: 1.7;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-left: 20px;
  margin-bottom: 0.8em;
}

.markdown-body :deep(pre) {
  overflow-x: auto;
  padding: 12px 14px;
  margin: 0.8em 0;
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
}
</style>
