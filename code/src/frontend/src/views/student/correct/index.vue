<!-- eslint-disable vue/no-v-html -->
<template>
  <div class="h-full">
    <n-card title="练习纠错" :bordered="false" class="rounded-8px shadow-sm">
      <div class="pb-12px text-16px">提交自己的作答内容，系统会结合参考答案与知识库给出纠错反馈。</div>

      <n-card title="作答信息" :bordered="false" class="mt-10px rounded-8px shadow-sm">
        <n-form ref="formRef" :model="formModel" :rules="rules" size="large" label-placement="left">
          <n-form-item label="题目" path="question">
            <n-input
              v-model:value="formModel.question"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              placeholder="请输入练习题目"
            />
          </n-form-item>
          <n-form-item label="你的答案" path="student_answer">
            <n-input
              v-model:value="formModel.student_answer"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 8 }"
              placeholder="请输入你的作答内容"
            />
          </n-form-item>
          <n-form-item label="参考答案（可选）" path="reference_answer">
            <n-input
              v-model:value="formModel.reference_answer"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 6 }"
              placeholder="如果你已有参考答案，可以一并提交"
            />
          </n-form-item>
          <n-space :size="12">
            <n-button type="primary" size="large" :loading="isLoading" @click="handleSubmit">
              {{ isLoading ? '批改中...' : '提交批改' }}
            </n-button>
            <n-button size="large" @click="resetForm">清空</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-space vertical class="mt-20px">
        <n-card title="纠错反馈" size="huge" :bordered="false" class="rounded-8px shadow-sm">
          <template v-if="feedbackContent">
            <div class="markdown-body" v-html="feedbackHtml"></div>
          </template>
          <template v-else>
            <n-empty description="提交作答后，这里会显示纠错反馈。" />
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

defineOptions({ name: 'StudentCorrectPage' });

interface CorrectFormModel {
  question: string;
  student_answer: string;
  reference_answer: string;
}

interface CorrectionResponse {
  status: string;
  feedback: string;
  corrected_at: string;
}

const auth = useAuthStore();
const formRef = ref<FormInst | null>(null);
const isLoading = ref(false);
const feedbackContent = ref('');

const formModel = reactive<CorrectFormModel>({
  question: '',
  student_answer: '',
  reference_answer: ''
});

const feedbackHtml = computed(() => marked.parse(feedbackContent.value || ''));

const rules: FormRules = {
  question: formRules.question,
  student_answer: formRules.student_answer
};

async function handleSubmit() {
  try {
    await formRef.value?.validate();
    isLoading.value = true;
    feedbackContent.value = '';

    const response = await _axios.post<CorrectionResponse>('/api/student/practice/correct', {
      question: formModel.question,
      student_answer: formModel.student_answer,
      reference_answer: formModel.reference_answer || null,
      student_id: Number(auth.userInfo.userId)
    });

    if (response.data.status !== 'success') {
      throw new Error('练习纠错失败');
    }

    feedbackContent.value = response.data.feedback;
    window.$message?.success('纠错完成');
  } catch (error: any) {
    console.error('练习纠错失败:', error);
    window.$message?.error(error?.response?.data?.detail || error?.message || '练习纠错失败');
  } finally {
    isLoading.value = false;
  }
}

function resetForm() {
  formModel.question = '';
  formModel.student_answer = '';
  formModel.reference_answer = '';
  feedbackContent.value = '';
  formRef.value?.restoreValidation();
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
</style>
