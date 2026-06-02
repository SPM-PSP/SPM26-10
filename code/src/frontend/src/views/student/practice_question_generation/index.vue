<!-- eslint-disable vue/no-v-html -->
<template>
  <div :class="['h-full', theme.darkMode ? 'page-dark' : 'page-light']">
    <n-space vertical :size="20">
      <n-card title="练习生成" :bordered="false" class="rounded-8px shadow-sm">
        <div class="pb-12px text-16px">按知识点、题型和数量生成结构化练习。生成后的练习会保存到你的个人练习库中，可重复查看、作答和删除。</div>

        <n-form ref="formRef" :model="formModel" :rules="rules" size="large" label-placement="left">
          <n-grid cols="1 l:3" responsive="screen" :x-gap="16" :y-gap="8">
            <n-grid-item span="1 l:2">
              <n-form-item label="知识点" path="topic_focus">
                <n-input
                  v-model:value="formModel.topic_focus"
                  placeholder="例如：进程通信、设备驱动、文件系统"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 4 }"
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="题型" path="question_type">
                <n-select v-model:value="formModel.question_type" :options="questionTypeOptions" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="题目数量" path="num_questions">
                <n-select v-model:value="formModel.num_questions" :options="numQuestionOptions" />
              </n-form-item>
            </n-grid-item>
          </n-grid>

          <n-space>
            <n-button type="primary" size="large" :loading="isLoading" @click="handleSubmit">
              {{ isLoading ? '生成中...' : '生成练习' }}
            </n-button>
            <n-button @click="fetchGeneratedPractices">刷新练习库</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-grid cols="1 l:2" responsive="screen" :x-gap="16" :y-gap="16">
        <n-grid-item>
          <n-card title="我的练习库" :bordered="false" class="rounded-8px shadow-sm">
            <n-space vertical :size="12">
              <template v-if="generatedPractices.length">
                <n-card
                  v-for="item in generatedPractices"
                  :key="item.id"
                  :bordered="false"
                  :class="['rounded-8px practice-card', selectedPractice?.id === item.id ? 'practice-card--active' : '']"
                  hoverable
                  @click="selectPractice(item.id)"
                >
                  <n-space vertical :size="8">
                    <div class="text-17px font-600">{{ item.title }}</div>
                    <div class="text-13px text-#64748b">创建时间：{{ formatDate(item.created_at) }}</div>
                    <div class="text-13px text-#64748b">
                      题目数：{{ item.questions.length }} ｜ 题型：{{ item.metadata_json?.question_type || '未标注' }}
                    </div>
                    <n-space :size="10">
                      <n-button size="small" @click.stop="selectPractice(item.id)">查看/作答</n-button>
                      <n-popconfirm @positive-click="deletePractice(item.id)">
                        <template #trigger>
                          <n-button size="small" type="error" ghost @click.stop>删除</n-button>
                        </template>
                        删除后将无法再次查看这套练习，确认继续？
                      </n-popconfirm>
                    </n-space>
                  </n-space>
                </n-card>
              </template>
              <template v-else>
                <n-empty description="你还没有生成任何练习。" />
              </template>
            </n-space>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="练习作答" :bordered="false" class="rounded-8px shadow-sm">
            <template v-if="selectedPractice">
              <n-space vertical :size="16">
                <div class="text-22px font-700">{{ selectedPractice.title }}</div>
                <div class="text-13px text-#64748b">
                  创建时间：{{ formatDate(selectedPractice.created_at) }} ｜ 题目数：{{ selectedPractice.questions.length }}
                </div>

                <n-card
                  v-for="question in selectedPractice.questions"
                  :key="question.id"
                  :bordered="false"
                  :class="['rounded-8px section-surface-card', theme.darkMode ? 'section-surface-card--dark' : 'section-surface-card--light']"
                >
                  <n-space vertical :size="10">
                    <div class="text-15px font-600">
                      {{ question.sort_order }}. {{ question.question_content }}
                    </div>
                    <div class="text-12px text-#64748b">
                      题型：{{ question.question_type }} ｜ 难度：{{ question.difficulty_level || '未标注' }} ｜ 分值：{{ question.score }}
                    </div>

                    <template v-if="question.question_type === '选择题' && question.options.length">
                      <n-radio-group v-model:value="answerMap[question.id]">
                        <n-space vertical :size="8">
                          <n-radio
                            v-for="(option, index) in question.options"
                            :key="`${question.id}-${index}`"
                            :value="option"
                          >
                            {{ String.fromCharCode(65 + index) }}. {{ option }}
                          </n-radio>
                        </n-space>
                      </n-radio-group>
                    </template>
                    <template v-else>
                      <n-input
                        v-model:value="answerMap[question.id]"
                        type="textarea"
                        :autosize="{ minRows: 3, maxRows: 8 }"
                        placeholder="请输入你的答案"
                      />
                    </template>
                  </n-space>
                </n-card>

                <n-space>
                  <n-button type="primary" :loading="submitting" @click="submitPractice">提交练习</n-button>
                  <n-button @click="resetAnswers">清空本次答案</n-button>
                </n-space>
              </n-space>
            </template>
            <template v-else>
              <n-empty description="选择一套练习后，这里会显示可直接作答的题目。" />
            </template>
          </n-card>
        </n-grid-item>
      </n-grid>

      <n-grid cols="1 l:2" responsive="screen" :x-gap="16" :y-gap="16">
        <n-grid-item>
          <n-card title="练习 Markdown 预览" :bordered="false" class="rounded-8px shadow-sm">
            <template v-if="selectedPractice?.content">
              <div class="markdown-body" v-html="selectedPracticeHtml"></div>
            </template>
            <template v-else>
              <n-empty description="选择一套练习后，这里会显示原始 Markdown 预览。" />
            </template>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="批改结果" :bordered="false" class="rounded-8px shadow-sm">
            <template v-if="submissionResult">
              <n-space vertical :size="16">
                <div class="text-18px font-700">
                  得分：{{ submissionResult.total_score }} / {{ submissionResult.max_score }}
                </div>
                <div class="text-14px text-#64748b">
                  正确率：{{ formatPercentage(submissionResult.correctness_percentage) }}
                </div>
                <n-card
                  v-for="item in submissionResult.answers"
                  :key="item.question_id"
                  :bordered="false"
                  class="rounded-8px bg-#f8fafc"
                >
                  <n-space vertical :size="8">
                    <div class="font-600">{{ item.question_content }}</div>
                    <div class="text-13px text-#64748b">你的答案：{{ item.student_answer || '未作答' }}</div>
                    <div class="text-13px text-#64748b">参考答案：{{ item.reference_answer || '无' }}</div>
                    <div class="text-13px text-#0f766e">得分：{{ item.score }} / {{ item.max_score }}</div>
                    <div class="markdown-body" v-html="renderMarkdown(item.auto_feedback || '暂无反馈')"></div>
                  </n-space>
                </n-card>
              </n-space>
            </template>
            <template v-else>
              <n-empty description="提交练习后，这里会显示逐题批改结果。" />
            </template>
          </n-card>
        </n-grid-item>
      </n-grid>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import type { FormInst, FormRules } from 'naive-ui';
import { marked } from 'marked';
import { useAuthStore, useThemeStore } from '@/store';
import { formRules } from '@/utils';
import _axios from '@/utils/request';
import type { GeneratedQuestionSet } from '@/types/assessment';

defineOptions({ name: 'StudentPracticeGenerationPage' });
const theme = useThemeStore();

interface PracticeFormModel {
  topic_focus: string;
  question_type: '选择题' | '填空题' | '简答题' | '编程题' | '混合';
  num_questions: number;
}

interface PracticeResponse {
  status: 'success' | 'error';
  practice_questions: string;
  generated_at: string;
  resource_id: string;
  questions: GeneratedQuestionSet['questions'];
}

interface PracticeSubmissionAnswer {
  question_id: string;
  question_content: string;
  question_type: string;
  reference_answer?: string | null;
  student_answer: string;
  auto_feedback?: string | null;
  score: number;
  max_score: number;
}

interface PracticeSubmissionResult {
  resource_id: string;
  total_score: number;
  max_score: number;
  correctness_percentage?: number | null;
  answers: PracticeSubmissionAnswer[];
}

const auth = useAuthStore();
const formRef = ref<FormInst | null>(null);
const isLoading = ref(false);
const submitting = ref(false);
const generatedPractices = ref<GeneratedQuestionSet[]>([]);
const selectedPractice = ref<GeneratedQuestionSet | null>(null);
const submissionResult = ref<PracticeSubmissionResult | null>(null);
const answerMap = reactive<Record<string, string>>({});

const formModel = reactive<PracticeFormModel>({
  topic_focus: '',
  question_type: '混合',
  num_questions: 3
});

const selectedPracticeHtml = computed(() => marked.parse(selectedPractice.value?.content || ''));

const questionTypeOptions = [
  { label: '混合', value: '混合' },
  { label: '选择题', value: '选择题' },
  { label: '填空题', value: '填空题' },
  { label: '简答题', value: '简答题' },
  { label: '编程题', value: '编程题' }
];

const numQuestionOptions = Array.from({ length: 8 }, (_, index) => ({
  label: `${index + 1} 题`,
  value: index + 1
}));

const rules: FormRules = {
  topic_focus: formRules.topic,
  question_type: formRules.question_type,
  num_questions: formRules.num_questions
};

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN');
}

function formatPercentage(value?: number | null) {
  return `${Math.round((value || 0) * 100)}%`;
}

function renderMarkdown(content: string) {
  return marked.parse(content);
}

function resetAnswers() {
  Object.keys(answerMap).forEach(key => delete answerMap[key]);
  for (const question of selectedPractice.value?.questions || []) {
    answerMap[question.id] = '';
  }
}

async function fetchGeneratedPractices() {
  try {
    const response = await _axios.get<GeneratedQuestionSet[]>('/api/student/generated-practices');
    generatedPractices.value = response.data;
    if (selectedPractice.value) {
      const latest = response.data.find(item => item.id === selectedPractice.value?.id);
      if (latest) {
        selectedPractice.value = latest;
        resetAnswers();
      }
    }
  } catch (error: any) {
    console.error('加载练习库失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载练习库失败');
  }
}

async function selectPractice(id: string) {
  try {
    const response = await _axios.get<GeneratedQuestionSet>(`/api/student/generated-practices/${id}`);
    selectedPractice.value = response.data;
    submissionResult.value = null;
    resetAnswers();
  } catch (error: any) {
    console.error('加载练习详情失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载练习详情失败');
  }
}

async function deletePractice(id: string) {
  try {
    await _axios.delete(`/api/student/generated-practices/${id}`);
    if (selectedPractice.value?.id === id) {
      selectedPractice.value = null;
      submissionResult.value = null;
      resetAnswers();
    }
    await fetchGeneratedPractices();
    window.$message?.success('练习删除成功');
  } catch (error: any) {
    console.error('删除练习失败:', error);
    window.$message?.error(error?.response?.data?.detail || '删除练习失败');
  }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate();
    isLoading.value = true;
    const response = await _axios.post<PracticeResponse>('/api/student/practice/generate', {
      student_id: Number(auth.userInfo.userId),
      topic_focus: formModel.topic_focus,
      question_type: formModel.question_type,
      num_questions: formModel.num_questions
    });

    if (response.data.status !== 'success') {
      throw new Error('练习生成失败');
    }

    await fetchGeneratedPractices();
    await selectPractice(response.data.resource_id);
    window.$message?.success('练习生成成功');
  } catch (error: any) {
    console.error('生成练习失败:', error);
    window.$message?.error(error?.response?.data?.detail || error?.message || '练习生成失败');
  } finally {
    isLoading.value = false;
  }
}

async function submitPractice() {
  if (!selectedPractice.value) return;
  try {
    submitting.value = true;
    const response = await _axios.post<PracticeSubmissionResult>(`/api/student/practices/${selectedPractice.value.id}/submit`, {
      answers: selectedPractice.value.questions.map(question => ({
        question_id: question.id,
        student_answer: answerMap[question.id] || ''
      }))
    });
    submissionResult.value = response.data;
    window.$message?.success('练习提交成功');
  } catch (error: any) {
    console.error('提交练习失败:', error);
    window.$message?.error(error?.response?.data?.detail || '提交练习失败');
  } finally {
    submitting.value = false;
  }
}

onMounted(fetchGeneratedPractices);
</script>

<style scoped>
.practice-card {
  cursor: pointer;
}

.practice-card--active {
  outline: 1px solid rgb(59 130 246 / 45%);
  background: rgb(239 246 255 / 70%);
}

.page-dark .practice-card--active {
  background: rgb(30 41 59 / 88%);
}

.page-dark :deep(.n-card) {
  color: #e5e7eb;
}

.section-surface-card--light {
  background: #f8fafc;
}

.section-surface-card--dark {
  background: rgb(30 41 59 / 82%);
  border: 1px solid rgb(71 85 105 / 45%);
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
</style>
