<!-- eslint-disable no-console, vue/no-v-html -->
<template>
  <div class="h-full">
    <n-card title="在线问答" :bordered="false" class="rounded-8px shadow-sm">
      <n-space vertical class="mb-4">
        <n-card size="huge" title="智能回答">
          <div v-if="answerContent" class="markdown-body answer-content" v-html="answerHtml"></div>
          <div v-else-if="isLoading" class="text-gray-400">正在生成回答...</div>
          <div v-else class="text-gray-400">提交问题后，答案将显示在这里...</div>
        </n-card>
      </n-space>

      <n-card title="提问区域" :bordered="false" class="rounded-8px shadow-sm">
        <n-form ref="formRef" :model="questionData" :rules="question_form_rules" size="large">
          <n-form-item label="输入问题" path="question">
            <n-input
              v-model:value="questionData.question"
              placeholder="请输入您的问题"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 5 }"
            />
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
              {{ isLoading ? '提交中...' : '提交问题' }}
            </n-button>
          </n-space>
        </n-form>
      </n-card>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import type { FormInst } from 'naive-ui';
import { marked } from 'marked';
import { formRules } from '@/utils';
import type { OnlineQARequestPayload } from '@/types/qa';

// 表单引用
const formRef = ref<FormInst | null>(null);

// 加载状态
const isLoading = ref(false);

// 问题数据
const questionData = reactive<OnlineQARequestPayload>({
  question: ''
});

// 答案内容
const answerContent = ref<string | null>(null); // 初始化为 null 方便 v-if 判断

const answerHtml = computed(() => {
  if (!answerContent.value) {
    return '';
  }
  return marked.parse(answerContent.value);
});

// 表单验证规则
// 假设 formRules 中有一个名为 `question` 的验证规则
const question_form_rules = {
  question: formRules.question // 确保 formRules.question 存在且有效
};

const BASE_URL = import.meta.env.VITE_APP_BASE_URL || 'http://127.0.0.1:8000';

// 提交处理
const handleSubmit = async (e: MouseEvent) => {
  e.preventDefault(); // 阻止表单默认提交行为
  try {
    // 表单验证
    await formRef.value?.validate();
    isLoading.value = true;
    answerContent.value = null; // 清空之前的答案

    // 构造请求体
    const requestPayload: OnlineQARequestPayload = {
      question: questionData.question
    };

    const sessionId = sessionStorage.getItem('session_id');
    const response = await fetch(`${BASE_URL}/api/student/ask/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(sessionId ? { 'X-Session-ID': sessionId } : {})
      },
      body: JSON.stringify(requestPayload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `请求失败: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('浏览器未返回可读取的流。');
    }

    answerContent.value = '';
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      answerContent.value += decoder.decode(value, { stream: true });
    }

    answerContent.value += decoder.decode();
    window.$message?.success('问题提交成功！');
  } catch (error) {
    console.error('提交问题失败:', error);
    window.$message?.error(`提交失败: ${(error as Error).message || '未知错误'}`);
    answerContent.value = null; // 提交失败也清空答案
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.answer-content {
  line-height: 1.6;
}

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

.markdown-body :deep(li) {
  margin-bottom: 0.4em;
}

.markdown-body :deep(pre) {
  overflow-x: auto;
  padding: 12px 14px;
  margin: 0.8em 0;
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
}

.markdown-body :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.markdown-body :deep(:not(pre) > code) {
  padding: 0.15em 0.4em;
  border-radius: 6px;
  background: rgb(148 163 184 / 18%);
}

.markdown-body :deep(blockquote) {
  padding-left: 12px;
  margin: 0.8em 0;
  border-left: 4px solid rgb(99 102 241 / 45%);
  color: #64748b;
}

.markdown-body :deep(table) {
  width: 100%;
  margin: 1em 0;
  border-collapse: collapse;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 8px 10px;
  text-align: left;
  border: 1px solid #dbe2ea;
}

.markdown-body :deep(th) {
  background: #f8fafc;
}
</style>
