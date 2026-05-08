<template>
  <div class="h-full">
    <n-card title="答案批改" :bordered="false" class="rounded-8px shadow-sm">
      <div class="pb-12px text-16px">自动化检测学生答案，提供错误定位与修正建议</div>
      <n-card title="课程信息" :bordered="false" class="mt-10px rounded-8px shadow-sm">
        <n-form ref="formRef" :model="answer" :rules="answer_data_rules" size="large" :show-label="true">
          <n-form-item label="题目" path="question">
            <n-input v-model:value="answer.question" placeholder="请输入题目" />
          </n-form-item>
          <n-form-item label="学生答案" path="student_answer">
            <n-input v-model:value="answer.student_answer" placeholder="请输入学生答案" />
          </n-form-item>
          <n-form-item label="参考答案" path="reference_answer">
            <n-input v-model:value="answer.reference_answer" placeholder="请输入参考答案" />
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
      <n-space vertical>
        <n-card title="批改结果" size="huge">卡片内容</n-card>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import type { FormInst } from 'naive-ui';
import { formRules } from '@/utils';

const formRef = ref<HTMLElement & FormInst>();
const isLoading = ref(false);

const answer = reactive({
  question: '',
  student_answer: '',
  reference_answer: ''
});

const answer_data_rules = {
  question: formRules.question,
  student_answer: formRules.student_answer,
  reference_answer: formRules.reference_answer
};

const handleSubmit = async () => {
  try {
    isLoading.value = true;
    await formRef.value?.validate();
    window.$message?.success('提交成功！');
    // 这里添加实际提交逻辑
    // 例如: await api.submit(course_data);
  } catch (errors) {
    window.$message?.error('请检查表单');
  } finally {
    isLoading.value = false;
  }
};

const resetForm = () => {
  answer.question = '';
  answer.student_answer = '';
  answer.reference_answer = '';
  formRef.value?.restoreValidation();
  window.$message?.info('表单已重置');
};
</script>

<style scoped></style>
