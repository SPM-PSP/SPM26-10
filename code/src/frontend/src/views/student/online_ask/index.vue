<!-- eslint-disable no-console, vue/no-v-html -->
<template>
  <div class="h-full">
    <n-card :title="pageTitle" :bordered="false" class="rounded-8px shadow-sm">
      <n-space vertical class="mb-4">
        <n-card :bordered="false" class="rounded-8px bg-#f8fafc dark:bg-#0f172a">
          <n-space vertical :size="10">
            <n-tag :type="roleTagType" round>{{ roleLabel }}</n-tag>
            <div class="text-18px font-600">{{ pageHeadline }}</div>
            <div class="text-14px text-gray-500">{{ pageDescription }}</div>
            <n-space wrap>
              <n-button v-for="item in suggestedQuestions" :key="item" size="small" secondary @click="fillQuestion(item)">
                {{ item }}
              </n-button>
            </n-space>
          </n-space>
        </n-card>

      </n-space>
      <n-space vertical class="mb-4">
        <n-card size="huge" title="智能回答">
          <div v-if="answerContent" class="markdown-body answer-content" v-html="answerHtml"></div>
          <div v-else-if="isLoading" class="text-gray-400">正在生成回答...</div>
          <div v-else class="text-gray-400">{{ emptyDescription }}</div>
        </n-card>
      </n-space>

      <n-card :title="formTitle" :bordered="false" class="rounded-8px shadow-sm">
        <n-form ref="formRef" :model="questionData" :rules="question_form_rules" size="large">
          <n-form-item label="输入问题" path="question">
            <n-input
              v-model:value="questionData.question"
              :placeholder="inputPlaceholder"
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
import { useAuthStore } from '@/store';
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
const auth = useAuthStore();

const roleTextMap: Record<Auth.RoleType, string> = {
  student: '学生端',
  teacher: '教师端',
  admin: '管理端'
};

const roleTagMap: Record<Auth.RoleType, 'success' | 'info' | 'error'> = {
  student: 'success',
  teacher: 'info',
  admin: 'error'
};

const contentMap: Record<
  Auth.RoleType,
  {
    pageTitle: string;
    headline: string;
    description: string;
    placeholder: string;
    formTitle: string;
    emptyDescription: string;
    suggestions: string[];
  }
> = {
  student: {
    pageTitle: '在线问答',
    headline: '围绕课程知识点提问，获得即时学习辅助。',
    description: '适合用于课后复习、概念辨析和练习前查漏补缺。',
    placeholder: '例如：什么是 Linux 内核模块？',
    formTitle: '学习提问',
    emptyDescription: '提交问题后，这里会显示基于知识库生成的回答。',
    suggestions: ['什么是 Linux 内核模块？', '嵌入式 Linux 中设备驱动的作用是什么？', 'select 和 poll 有什么区别？']
  },
  teacher: {
    pageTitle: '教学问答',
    headline: '把它当作备课和课堂答疑的快速辅助入口。',
    description: '适合快速确认知识点表述、组织课堂解释或准备教学示例。',
    placeholder: '例如：请解释进程调度的核心概念',
    formTitle: '教学提问',
    emptyDescription: '提交问题后，这里会显示适合教学场景的辅助回答。',
    suggestions: ['请解释进程调度的核心概念', '如何向学生讲清楚文件系统挂载？', '设备树在嵌入式 Linux 中的作用是什么？']
  },
  admin: {
    pageTitle: '系统问答验证',
    headline: '这里用于验证公共问答链路在管理端也能正常工作。',
    description: '管理员不做内容创作，只保留联调和演示需要的问答入口。',
    placeholder: '例如：请解释中断处理流程',
    formTitle: '问答调试',
    emptyDescription: '提交问题后，这里会显示公共问答链路返回的结果。',
    suggestions: ['请解释中断处理流程', 'DMA 的基本作用是什么？', 'Linux 设备驱动通常包含哪些部分？']
  }
};

const roleLabel = computed(() => roleTextMap[auth.userInfo.userRole]);
const roleTagType = computed(() => roleTagMap[auth.userInfo.userRole]);
const pageConfig = computed(() => contentMap[auth.userInfo.userRole]);
const pageTitle = computed(() => pageConfig.value.pageTitle);
const pageHeadline = computed(() => pageConfig.value.headline);
const pageDescription = computed(() => pageConfig.value.description);
const inputPlaceholder = computed(() => pageConfig.value.placeholder);
const formTitle = computed(() => pageConfig.value.formTitle);
const emptyDescription = computed(() => pageConfig.value.emptyDescription);
const suggestedQuestions = computed(() => pageConfig.value.suggestions);

function fillQuestion(question: string) {
  questionData.question = question;
}

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
