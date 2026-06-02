<!-- eslint-disable vue/no-v-html -->
<template>
  <div class="h-full">
    <n-space vertical :size="20">
      <n-card title="考核题目生成" :bordered="false" class="rounded-8px shadow-sm">
        <div class="pb-12px text-16px">设置考察内容、题型与难度，系统会生成结构化题目并保存到你的题库。</div>
        <n-form ref="formRef" :model="assessment" :rules="assessmentRules" size="large" :show-label="true">
          <n-form-item label="考察内容" path="topic">
            <n-input v-model:value="assessment.topic" placeholder="请输入考察内容" />
          </n-form-item>
          <n-grid cols="1 l:3" responsive="screen" :x-gap="16">
            <n-grid-item>
              <n-form-item label="题型" path="question_type">
                <n-select v-model:value="assessment.question_type" :options="questionTypeOptions" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="难度" path="difficulty_level">
                <n-select v-model:value="assessment.difficulty_level" :options="difficultyLevelOptions" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="题目数量" path="num_questions">
                <n-select v-model:value="assessment.num_questions" :options="numQuestionsOptions" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-button type="primary" size="large" :loading="isLoading" @click="handleSubmit">
            {{ isLoading ? '生成中...' : '生成考核题目' }}
          </n-button>
        </n-form>
      </n-card>

      <n-grid cols="1 l:2" responsive="screen" :x-gap="16" :y-gap="16">
        <n-grid-item>
          <n-card title="已生成考核题" :bordered="false" class="rounded-8px shadow-sm">
            <n-space justify="space-between" align="center">
              <div class="text-14px text-#64748b">你生成的考核题会保存在这里，可重复查看或删除。</div>
              <n-button @click="fetchGeneratedAssessments">刷新</n-button>
            </n-space>

            <n-space vertical :size="12" class="mt-16px">
              <template v-if="generatedAssessments.length">
                <n-card
                  v-for="item in generatedAssessments"
                  :key="item.id"
                  :bordered="false"
                  :class="['rounded-8px assessment-card', selectedAssessment?.id === item.id ? 'assessment-card--active' : '']"
                  hoverable
                  @click="selectAssessment(item.id)"
                >
                  <n-space vertical :size="8">
                    <div class="text-17px font-600">{{ item.title }}</div>
                    <div class="text-13px text-#64748b">创建时间：{{ formatDate(item.created_at) }}</div>
                    <div class="text-13px text-#64748b">
                      题目数：{{ item.questions.length }} ｜ 题型：{{ item.metadata_json?.question_type || '未标注' }}
                    </div>
                    <n-space :size="10">
                      <n-button size="small" @click.stop="selectAssessment(item.id)">查看</n-button>
                      <n-popconfirm @positive-click="deleteAssessment(item.id)">
                        <template #trigger>
                          <n-button size="small" type="error" ghost @click.stop>删除</n-button>
                        </template>
                        删除后将无法再追加到试卷草稿中，确认继续？
                      </n-popconfirm>
                    </n-space>
                  </n-space>
                </n-card>
              </template>
              <template v-else>
                <n-empty description="还没有生成考核题。" />
              </template>
            </n-space>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="考核题详情" :bordered="false" class="rounded-8px shadow-sm">
            <template v-if="selectedAssessment">
              <n-space vertical :size="16">
                <div class="text-22px font-700">{{ selectedAssessment.title }}</div>
                <div class="text-13px text-#64748b">
                  创建时间：{{ formatDate(selectedAssessment.created_at) }} ｜ 题目数：{{ selectedAssessment.questions.length }}
                </div>

                <n-card v-for="question in selectedAssessment.questions" :key="question.id" :bordered="false" class="rounded-8px bg-#f8fafc">
                  <n-space vertical :size="10">
                    <div class="text-15px font-600">
                      {{ question.sort_order }}. {{ question.question_content }}
                    </div>
                    <div class="text-12px text-#64748b">
                      题型：{{ question.question_type }} ｜ 难度：{{ question.difficulty_level || '未标注' }} ｜ 分值：{{ question.score }}
                    </div>
                    <div v-if="question.question_type === '选择题' && question.options.length" class="text-14px text-#475569">
                      <div v-for="(option, index) in question.options" :key="`${question.id}-${index}`">
                        {{ String.fromCharCode(65 + index) }}. {{ option }}
                      </div>
                    </div>
                    <div class="text-14px text-#0f766e">参考答案：{{ question.reference_answer || '无' }}</div>
                  </n-space>
                </n-card>

                <n-card title="Markdown 预览" :bordered="false" class="rounded-8px bg-#f8fafc">
                  <div class="markdown-body" v-html="assessmentHtml"></div>
                </n-card>
              </n-space>
            </template>
            <template v-else>
              <n-empty description="选择一套已生成的考核题后，这里会显示详细内容。" />
            </template>
          </n-card>
        </n-grid-item>
      </n-grid>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import type { FormInst } from 'naive-ui';
import { marked } from 'marked';
import { formRules } from '@/utils';
import _axios from '@/utils/request';
import type { AssessmentRequestPayload, AssessmentApiResponse, GeneratedQuestionSet } from '@/types/assessment';

const formRef = ref<HTMLElement & FormInst>();
const isLoading = ref(false);
const generatedAssessments = ref<GeneratedQuestionSet[]>([]);
const selectedAssessment = ref<GeneratedQuestionSet | null>(null);

const assessmentHtml = computed(() => marked.parse(selectedAssessment.value?.content || ''));

const assessment = reactive<AssessmentRequestPayload>({
  topic: '',
  question_type: '选择题',
  difficulty_level: '中等',
  num_questions: 3
});

const questionTypeOptions = [
  { label: '选择题', value: '选择题' },
  { label: '填空题', value: '填空题' },
  { label: '简答题', value: '简答题' },
  { label: '编程题', value: '编程题' }
];

const difficultyLevelOptions = [
  { label: '简单', value: '简单' },
  { label: '中等', value: '中等' },
  { label: '困难', value: '困难' }
];

const numQuestionsOptions = Array.from({ length: 20 }, (_, i) => ({
  label: `${i + 1}题`,
  value: i + 1
}));

const assessmentRules = {
  topic: formRules.topic,
  question_type: formRules.question_type,
  difficulty_level: formRules.difficulty_level,
  num_questions: formRules.num_questions
};

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN');
}

async function fetchGeneratedAssessments() {
  try {
    const response = await _axios.get<GeneratedQuestionSet[]>('/api/teacher/generated-assessments');
    generatedAssessments.value = response.data;
    if (selectedAssessment.value) {
      const latest = response.data.find(item => item.id === selectedAssessment.value?.id);
      if (latest) {
        selectedAssessment.value = latest;
      }
    }
  } catch (error: any) {
    console.error('加载考核题列表失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载考核题列表失败');
  }
}

async function selectAssessment(id: string) {
  try {
    const response = await _axios.get<GeneratedQuestionSet>(`/api/teacher/generated-assessments/${id}`);
    selectedAssessment.value = response.data;
  } catch (error: any) {
    console.error('加载考核题详情失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载考核题详情失败');
  }
}

async function deleteAssessment(id: string) {
  try {
    await _axios.delete(`/api/teacher/generated-assessments/${id}`);
    if (selectedAssessment.value?.id === id) {
      selectedAssessment.value = null;
    }
    await fetchGeneratedAssessments();
    window.$message?.success('考核题删除成功');
  } catch (error: any) {
    console.error('删除考核题失败:', error);
    window.$message?.error(error?.response?.data?.detail || '删除考核题失败');
  }
}

const handleSubmit = async () => {
  try {
    isLoading.value = true;
    await formRef.value?.validate();
    const response = await _axios.post<AssessmentApiResponse>('/api/teacher/assessment/generate', assessment);
    if (response.data.status === 'success') {
      window.$message?.success('考核题目生成成功');
      await fetchGeneratedAssessments();
      await selectAssessment(response.data.resource_id);
    } else {
      window.$message?.error('考核题目生成失败');
    }
  } catch (error: any) {
    console.error('生成考核题失败:', error);
    window.$message?.error(error?.response?.data?.detail || '请检查表单填写或网络状况');
  } finally {
    isLoading.value = false;
  }
};

onMounted(fetchGeneratedAssessments);
</script>

<style scoped>
.assessment-card {
  cursor: pointer;
}

.assessment-card--active {
  outline: 1px solid rgb(59 130 246 / 45%);
  background: rgb(239 246 255 / 70%);
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
</style>
