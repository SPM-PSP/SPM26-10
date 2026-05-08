<!-- eslint-disable vue/no-v-html -->
<template>
  <div class="h-full">
    <n-card title="答案批改" :bordered="false" class="rounded-8px shadow-sm">
      <div class="pb-12px text-16px">自动化检测学生答案，提供错误定位与修正建议</div>
      <n-card title="课程信息" :bordered="false" class="mt-10px rounded-8px shadow-sm">
        <n-form ref="formRef" :model="answer" :rules="answer_data_rules" size="large" :show-label="true">
          <n-form-item label="题目" path="question">
            <n-input v-model:value="answer.question" type="textarea" :rows="3" placeholder="请输入题目" />
          </n-form-item>
          <n-form-item label="学生答案" path="student_answer">
            <n-input v-model:value="answer.student_answer" type="textarea" :rows="5" placeholder="请输入学生答案" />
          </n-form-item>
          <n-form-item label="参考答案" path="reference_answer">
            <n-input v-model:value="answer.reference_answer" type="textarea" :rows="5" placeholder="请输入参考答案" />
          </n-form-item>
          <n-space :vertical="true" :size="18">
            <div class="grid grid-cols-2 gap-18px">
              <n-button
                type="primary"
                size="large"
                :block="true"
                :round="true"
                :loading="isLoading"
                @click="handleSubmit"
              >
                {{ isLoading ? '批改中...' : '批改' }}
              </n-button>
              <n-button type="primary" size="large" :block="true" :round="true" @click="resetForm">再改一题</n-button>
            </div>
          </n-space>
        </n-form>
      </n-card>

      <n-space vertical class="mt-20px">
        <n-card title="批改结果" size="huge" :bordered="false" class="rounded-8px shadow-sm">
          <template v-if="feedbackContent">
            // eslint-disable-next-line vue/no-v-html, vue/no-v-html
            <div class="markdown-body" v-html="feedbackHtml"></div>
          </template>
          <template v-else>
            <n-empty description="提交答案后将在此处显示批改结果" />
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
import type { AnswerCorrectRequestPayload, AnswerCorrectApiResponse } from '@/types/answer'; // 导入我们定义的类型

// 表单引用
const formRef = ref<HTMLElement & FormInst>();
// 加载状态
const isLoading = ref(false);
// 批改反馈内容 (Markdown 格式)
const feedbackContent = ref<string | null>(null);

// 使用 computed 属性将 Markdown 转换为 HTML
const feedbackHtml = computed(() => {
  if (feedbackContent.value) {
    // marked.parse() 将 Markdown 字符串转换为 HTML 字符串
    return marked.parse(feedbackContent.value);
  }
  return ''; // 如果没有内容，返回空字符串
});

// 表单数据
const answer = reactive<AnswerCorrectRequestPayload>({
  question: '',
  student_answer: '',
  reference_answer: '',
  student_id: '3' // 假设学生ID固定为'3'，如果需要动态获取，请根据实际情况修改
});

const answer_data_rules = {
  question: formRules.question,
  student_answer: formRules.student_answer,
  reference_answer: formRules.reference_answer
};

const handleSubmit = async () => {
  try {
    isLoading.value = true;
    // 1. 表单验证
    await formRef.value?.validate();

    // 2. 构造请求体数据
    const requestPayload: AnswerCorrectRequestPayload = {
      question: answer.question,
      student_answer: answer.student_answer,
      reference_answer: answer.reference_answer,
      student_id: answer.student_id // 使用 reactive 对象中的 student_id
    };

    // 3. 调用接口
    const response = await _axios.post<AnswerCorrectApiResponse>('/api/teacher/student_answer/correct', requestPayload);

    // 4. 处理接口响应
    if (response.data.status === 'success') {
      window.$message?.success('答案批改成功！');
      feedbackContent.value = response.data.feedback; // 更新批改反馈内容
      // eslint-disable-next-line no-console
      console.log('批改反馈 (Markdown):', feedbackContent.value);
    } else {
      window.$message?.error(response.data.feedback || '答案批改失败！');
      feedbackContent.value = null; // 清空旧内容
    }
  } catch (errors) {
    window.$message?.error('请检查表单填写或网络状况');
    feedbackContent.value = null; // 清空旧内容
  } finally {
    isLoading.value = false; // 无论成功失败都关闭加载状态
  }
};

const resetForm = () => {
  answer.question = '';
  answer.student_answer = '';
  answer.reference_answer = '';
  feedbackContent.value = null; // 重置时清空批改结果
  formRef.value?.restoreValidation();
  window.$message?.info('表单已重置');
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
