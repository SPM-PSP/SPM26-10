<template>
  <div class="h-full">
    <n-card title="练习题目生成" :bordered="false" class="rounded-8px shadow-sm">
      <div class="pb-12px text-16px">根据学习内容智能生成练习题目</div>
      <n-card title="课程信息" :bordered="false" class="mt-10px rounded-8px shadow-sm">
        <n-form ref="formRef" :model="assesment" :rules="course_data_rules" size="large" :show-label="true">
          <n-form-item label="考察内容" path="topic">
            <n-input v-model:value="assesment.topic" placeholder="请输入考察内容" />
          </n-form-item>

          <n-form-item label="题目类型" path="question_type">
            <n-select
              v-model:value="assesment.question_type"
              :options="question_type_options"
              placeholder="请选择题目类型"
              filterable
            />
          </n-form-item>

          <n-form-item label="题目难度" path="difficulty_level">
            <n-select
              v-model:value="assesment.difficulty_level"
              :options="difficulty_level_options"
              placeholder="请选择题目难度"
              filterable
            />
          </n-form-item>

          <n-form-item label="题目数量" path="num_questions">
            <n-select
              v-model:value="assesment.num_questions"
              :options="num_questions_options"
              placeholder="请选择题目数量"
              filterable
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
              {{ isLoading ? '提交中...' : '提交' }}
            </n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-space vertical class="mt-20px">
        <n-card title="生成的练习题目" size="huge" :bordered="false" class="rounded-8px shadow-sm">
          <template v-if="generatedContent">
            // eslint-disable-next-line vue/no-v-html, vue/no-v-html, vue/no-v-html, vue/no-v-html, vue/no-v-html,
            vue/no-v-html // eslint-disable-next-line vue/no-v-html, vue/no-v-html, vue/no-v-html, vue/no-v-html,
            vue/no-v-html
            <div class="markdown-body" v-html="generatedHtml"></div>
          </template>
          <template v-else>
            <n-empty description="提交课程信息后将在此处显示练习题目" />
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
import { isAxiosError } from 'axios'; // 从 axios 导入 isAxiosError 函数
import { formRules } from '@/utils';
import _axios from '@/utils/request'; // 假设这是您的 Axios 实例
import { useAuthStore } from '@/store/modules/auth'; // 假设您需要用户ID

// 打印组件加载信息，用于调试
console.log('PracticeGeneration 组件脚本开始执行！');

const authStore = useAuthStore(); // 获取认证状态存储
console.log('authStore:', authStore);
// eslint-disable-next-line no-console
console.log('authStore.userInfo:', authStore.userInfo);
// eslint-disable-next-line no-console
console.log('authStore.userInfo?.userId:', authStore.userInfo?.userId);

const formRef = ref<HTMLElement & FormInst>();
const isLoading = ref(false);
const generatedContent = ref<string | null>(null); // 用于存储生成的题目内容 (Markdown 格式)

// 使用 computed 属性将 Markdown 转换为 HTML
const generatedHtml = computed(() => {
  if (generatedContent.value) {
    return marked.parse(generatedContent.value);
  }
  return '';
});

// 定义 AssesmentForm 接口，与请求体结构一致
interface AssesmentForm {
  topic: string;
  num_questions: number | null;
  question_type: string | null;
  difficulty_level: string | null;
}

// 定义后端返回的响应接口
interface PracticeApiReponse {
  status: 'success' | 'failure'; // 根据后端实际返回的 status 调整
  assessment_content: string;
  generated_at: string;
  resource_id: string;
  message?: string; // 某些失败情况下可能包含的 message
}

const assesment: AssesmentForm = reactive({
  topic: '',
  num_questions: null,
  question_type: null,
  difficulty_level: null
});

const num_questions_options = Array.from({ length: 99 }, (_, i) => ({
  label: `${i + 1}道`,
  value: i + 1
}));

const question_type_options = [
  { label: '选择题', value: '选择题' },
  { label: '简答题', value: '简答题' },
  { label: '编程题', value: '编程题' },
  { label: '混合', value: '混合' }
];

const difficulty_level_options = [
  { label: '简单', value: '简单' },
  { label: '中等', value: '中等' },
  { label: '困难', value: '困难' }
];

const course_data_rules = {
  topic: formRules.topic,
  question_type: formRules.question_type,
  difficulty_level: formRules.difficulty_level,
  num_questions: formRules.num_questions
};

const handleSubmit = async () => {
  try {
    isLoading.value = true;
    generatedContent.value = null; // 每次提交前清空之前生成的内容

    await formRef.value?.validate(); // 表单验证

    // 移除 userId 和 sessionId 的前端检查和传递，
    // 假设它们通过 Axios 拦截器或其他全局机制处理

    const requestBody: Omit<AssesmentForm, 'num_questions'> & { num_questions: number } = {
      topic: assesment.topic,
      num_questions: assesment.num_questions === null ? 0 : assesment.num_questions, // 确保 num_questions 是 number
      question_type: assesment.question_type,
      difficulty_level: assesment.difficulty_level
    };

    // 如果 num_questions 必须是非 null，而表单绑定是 null，则需要类型断言或确保数据有效
    if (requestBody.num_questions === 0 && assesment.num_questions === null) {
      window.$message?.error('请选择题目数量。');
      isLoading.value = false;
      return;
    }

    // eslint-disable-next-line no-console
    console.log('即将发送的请求体:', requestBody);

    // 调用接口，不在这里显式设置 X-Session-ID 和 Content-Type，
    // 而是假设 _axios 实例已经通过拦截器处理了这些
    const response = await _axios.post<PracticeApiReponse>('/api/teacher/assessment/generate', requestBody);

    // 检查响应头中的 X-Session-ID (仅用于调试，如果不需要可以移除)
    console.log('API 响应状态码:', response.status);
    // eslint-disable-next-line no-console
    console.log('API 响应头:', response.headers);
    const responseSessionId = response.headers['x-session-id'] || response.headers['X-Session-ID'];
    if (responseSessionId) {
      // eslint-disable-next-line no-console
      console.log('后端响应头中包含 X-Session-ID:', responseSessionId);
    } else {
      console.log('后端响应头中未包含 X-Session-ID。');
    }

    if (response.data && response.data.status === 'success') {
      window.$message?.success('题目生成成功！');
      generatedContent.value = response.data.assessment_content; // 存储并显示题目内容
      // eslint-disable-next-line no-console
      console.log('生成的题目内容:', response.data.assessment_content);
      console.log('资源ID:', response.data.resource_id);
    } else {
      // 假设后端在失败时也可能返回 assessment_content 或 message
      window.$message?.error(response.data.message || '题目生成失败！');
      generatedContent.value = null;
    }
  } catch (errors: unknown) {
    console.error('表单提交或API请求失败:', errors);
    generatedContent.value = null; // 错误时清空内容

    if (isAxiosError(errors)) {
      if (errors.response) {
        // 后端返回了错误响应
        const errorData = errors.response.data as { message?: string }; // 尝试获取后端错误消息
        window.$message?.error(`错误: ${errorData.message || errors.message || '服务器返回错误'}`);
      } else if (errors.request) {
        // 请求已发送但没有收到响应 (例如，网络断开或服务器未启动)
        window.$message?.error('请求已发送，但没有收到响应，请检查网络。');
      } else {
        // 其他错误 (例如，在设置请求时发生错误)
        window.$message?.error(`请求设置错误: ${errors.message}`);
      }
    } else if (errors instanceof Error) {
      // 其他非 Axios 错误
      window.$message?.error(`发生错误: ${errors.message}`);
    } else {
      // 无法识别的错误类型
      window.$message?.error(`发生未知错误: ${String(errors)}`);
    }
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
  list-style-type: disc; /* 确保列表点显示 */
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
