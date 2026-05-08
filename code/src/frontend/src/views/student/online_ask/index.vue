<!-- eslint-disable no-console -->
<template>
  <div class="h-full">
    <n-card title="在线问答" :bordered="false" class="rounded-8px shadow-sm">
      <n-space vertical class="mb-4">
        <n-card size="huge" title="智能回答">
          <div v-if="answerContent" class="answer-content">
            {{ answerContent }}
          </div>
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
import { ref, reactive } from 'vue';
import type { FormInst } from 'naive-ui';
import { formRules } from '@/utils';
import _axios from '@/utils/request'; // 引入封装的 axios 实例
import type { OnlineQARequestPayload, OnlineQAApiResponse } from '@/types/qa'; // 导入我们定义的类型

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

// 表单验证规则
// 假设 formRules 中有一个名为 `question` 的验证规则
const question_form_rules = {
  question: formRules.question // 确保 formRules.question 存在且有效
};

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

    // 发送请求，使用 _axios
    const response = await _axios.post<OnlineQAApiResponse>('/api/student/ask', requestPayload);

    // 处理响应
    if (response.data.status === 'success') {
      answerContent.value = response.data.answer;
      window.$message?.success('问题提交成功！');
      // 可以选择清空问题输入框
      // questionData.question = '';
    } else {
      // 假设后端在失败时返回 message 字段，或者使用 answer 字段作为错误信息
      throw new Error(response.data.answer || '获取答案失败');
    }
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
  white-space: pre-wrap; /* 保留空白符和换行符 */
  line-height: 1.6;
}
</style>
