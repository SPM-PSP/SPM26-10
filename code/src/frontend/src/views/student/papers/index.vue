<!-- eslint-disable vue/no-v-html -->
<template>
  <div :class="['h-full', theme.darkMode ? 'page-dark' : 'page-light']">
    <n-space vertical :size="20">
      <n-card title="班级试卷" :bordered="false" class="rounded-8px shadow-sm">
        <n-space align="center" justify="space-between" wrap>
          <n-space align="center" wrap>
            <span class="text-14px text-#64748b">选择班级</span>
            <n-select
              v-model:value="selectedClassId"
              class="w-280px"
              :options="classOptions"
              placeholder="请选择班级"
              @update:value="handleClassChange"
            />
          </n-space>
          <n-button @click="fetchClassesAndPapers">刷新</n-button>
        </n-space>
      </n-card>

      <n-grid cols="1 l:2" responsive="screen" :x-gap="16" :y-gap="16">
        <n-grid-item>
          <n-card title="已发布试卷" :bordered="false" class="rounded-8px shadow-sm">
            <n-spin :show="loadingList">
              <template v-if="papers.length">
                <n-space vertical :size="12">
                  <n-card
                    v-for="paper in papers"
                    :key="paper.publication_id"
                    :bordered="false"
                    :class="['rounded-8px paper-card', selectedPublicationId === paper.publication_id ? 'paper-card--active' : '']"
                    hoverable
                    @click="selectPaper(paper.publication_id)"
                  >
                    <n-space vertical :size="8">
                      <div class="text-17px font-600">{{ paper.title }}</div>
                      <div class="text-13px text-#64748b">班级：{{ paper.class_name }}</div>
                      <div class="text-13px text-#64748b">教师：{{ paper.teacher_name }}</div>
                      <div class="text-13px text-#64748b">
                        发布时间：{{ formatDate(paper.published_at) }}
                        <span v-if="paper.deadline">｜截止：{{ formatDate(paper.deadline) }}</span>
                      </div>
                      <div class="text-13px text-#64748b">总分：{{ paper.total_score }}</div>
                    </n-space>
                  </n-card>
                </n-space>
              </template>
              <template v-else>
                <n-empty description="当前班级还没有已发布试卷。" />
              </template>
            </n-spin>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="试卷作答" :bordered="false" class="rounded-8px shadow-sm">
            <n-spin :show="loadingDetail || submitting">
              <template v-if="paperDetail">
                <n-space vertical :size="18">
                  <div class="text-22px font-700">{{ paperDetail.paper.title }}</div>
                  <div class="text-13px text-#64748b">
                    班级：{{ paperDetail.class_name }} ｜ 教师：{{ paperDetail.teacher_name }} ｜ 总分：{{ paperDetail.paper.total_score }}
                  </div>

                  <n-card
                    v-for="section in paperDetail.paper.sections"
                    :key="section.id"
                    :bordered="false"
                    :class="['rounded-8px section-surface-card', theme.darkMode ? 'section-surface-card--dark' : 'section-surface-card--light']"
                  >
                    <n-space vertical :size="14">
                      <div class="text-18px font-600">{{ section.section_title }}</div>
                      <div
                        v-for="question in section.questions"
                        :key="question.id"
                        :class="['rounded-8px border border-solid p-14px question-surface-card', theme.darkMode ? 'question-surface-card--dark' : 'question-surface-card--light']"
                      >
                        <n-space vertical :size="10">
                          <div class="text-15px font-600">
                            {{ question.sort_order }}. {{ question.question_content }}
                          </div>
                          <div class="text-12px text-#64748b">
                            题型：{{ question.question_type }} ｜ 难度：{{ question.difficulty_level || '未标注' }} ｜ 分值：{{ question.score }}
                          </div>

                          <template v-if="question.question_type === '选择题' && question.metadata_json?.options?.length">
                            <n-radio-group v-model:value="answerMap[question.id]">
                              <n-space vertical :size="8">
                                <n-radio
                                  v-for="(option, index) in question.metadata_json.options"
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
                      </div>
                    </n-space>
                  </n-card>

                  <n-space>
                    <n-button type="primary" :loading="submitting" @click="submitPaper">提交试卷</n-button>
                    <n-button @click="loadPaperDetail(selectedPublicationId)">重载题目</n-button>
                  </n-space>
                </n-space>
              </template>
              <template v-else>
                <n-empty description="请先从左侧选择试卷。" />
              </template>
            </n-spin>
          </n-card>
        </n-grid-item>
      </n-grid>

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
              :key="item.id"
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
          <n-empty description="提交试卷后，这里会显示逐题批改结果。" />
        </template>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { marked } from 'marked';
import { useThemeStore } from '@/store';
import _axios from '@/utils/request';

defineOptions({ name: 'StudentPapersPage' });
const theme = useThemeStore();

interface ClassItem {
  id: string;
  name: string;
}

interface PaperListItem {
  id: string;
  publication_id: string;
  title: string;
  class_name: string;
  teacher_name: string;
  published_at: string;
  deadline?: string | null;
  status: string;
  total_score: number;
}

interface PaperQuestion {
  id: string;
  question_type: string;
  question_content: string;
  reference_answer?: string | null;
  score: number;
  difficulty_level?: string | null;
  sort_order: number;
  metadata_json?: {
    options?: string[];
    [key: string]: any;
  } | null;
}

interface PaperSection {
  id: string;
  section_title: string;
  source_module_name?: string | null;
  sort_order: number;
  questions: PaperQuestion[];
}

interface PaperDetail {
  id: string;
  title: string;
  total_score: number;
  sections: PaperSection[];
}

interface StudentPaperDetailResponse {
  publication_id: string;
  paper: PaperDetail;
  class_name: string;
  teacher_name: string;
  published_at: string;
  deadline?: string | null;
}

interface SubmissionAnswer {
  id: string;
  question_id: string;
  question_content: string;
  question_type: string;
  reference_answer?: string | null;
  student_answer: string;
  auto_feedback?: string | null;
  score: number;
  max_score: number;
}

interface SubmissionResult {
  id: string;
  total_score: number;
  max_score: number;
  correctness_percentage?: number | null;
  answers: SubmissionAnswer[];
}

const route = useRoute();
const loadingList = ref(false);
const loadingDetail = ref(false);
const submitting = ref(false);
const selectedClassId = ref<string | null>((route.query.classId as string) || null);
const selectedPublicationId = ref<string>('');
const classes = ref<ClassItem[]>([]);
const papers = ref<PaperListItem[]>([]);
const paperDetail = ref<StudentPaperDetailResponse | null>(null);
const submissionResult = ref<SubmissionResult | null>(null);
const answerMap = reactive<Record<string, string>>({});

const classOptions = computed(() => classes.value.map(item => ({ label: item.name, value: item.id })));

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '未设置';
}

function formatPercentage(value?: number | null) {
  return `${Math.round((value || 0) * 100)}%`;
}

function renderMarkdown(content: string) {
  return marked.parse(content);
}

function resetPaperState() {
  papers.value = [];
  paperDetail.value = null;
  submissionResult.value = null;
  selectedPublicationId.value = '';
  Object.keys(answerMap).forEach(key => delete answerMap[key]);
}

async function fetchClassesAndPapers() {
  loadingList.value = true;
  try {
    const classResponse = await _axios.get<ClassItem[]>('/api/student/classes');
    classes.value = classResponse.data;
    if (!classes.value.length) {
      selectedClassId.value = null;
      resetPaperState();
      return;
    }

    const requestedClassId = selectedClassId.value;
    const classExists = requestedClassId && classes.value.some(item => item.id === requestedClassId);
    selectedClassId.value = classExists ? requestedClassId : classes.value[0].id;
    await loadPapers();
  } catch (error: any) {
    console.error('获取班级或试卷失败:', error);
    window.$message?.error(error?.response?.data?.detail || '获取班级或试卷失败');
  } finally {
    loadingList.value = false;
  }
}

async function loadPapers() {
  resetPaperState();
  if (!selectedClassId.value) return;
  try {
    const response = await _axios.get<PaperListItem[]>(`/api/student/classes/${selectedClassId.value}/papers`);
    papers.value = response.data;
    if (papers.value.length) {
      await selectPaper(papers.value[0].publication_id);
    }
  } catch (error: any) {
    console.error('加载班级试卷列表失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载班级试卷列表失败');
  }
}

async function handleClassChange() {
  await loadPapers();
}

async function selectPaper(publicationId: string) {
  selectedPublicationId.value = publicationId;
  await loadPaperDetail(publicationId);
}

async function loadPaperDetail(publicationId?: string) {
  if (!publicationId) return;
  loadingDetail.value = true;
  submissionResult.value = null;
  try {
    const response = await _axios.get<StudentPaperDetailResponse>(`/api/student/papers/${publicationId}`);
    paperDetail.value = response.data;
    Object.keys(answerMap).forEach(key => delete answerMap[key]);
    for (const section of response.data.paper.sections) {
      for (const question of section.questions) {
        answerMap[question.id] = '';
      }
    }
  } catch (error: any) {
    console.error('加载试卷详情失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载试卷详情失败');
  } finally {
    loadingDetail.value = false;
  }
}

async function submitPaper() {
  if (!paperDetail.value || !selectedPublicationId.value) return;
  submitting.value = true;
  try {
    const answers = paperDetail.value.paper.sections.flatMap(section =>
      section.questions.map(question => ({
        question_id: question.id,
        student_answer: answerMap[question.id] || ''
      }))
    );
    const response = await _axios.post<SubmissionResult>(`/api/student/papers/${selectedPublicationId.value}/submit`, {
      answers
    });
    submissionResult.value = response.data;
    window.$message?.success('试卷提交成功');
  } catch (error: any) {
    console.error('提交试卷失败:', error);
    window.$message?.error(error?.response?.data?.detail || '提交试卷失败');
  } finally {
    submitting.value = false;
  }
}

onMounted(fetchClassesAndPapers);
</script>

<style scoped>
.paper-card {
  cursor: pointer;
}

.paper-card--active {
  outline: 1px solid rgb(59 130 246 / 45%);
  background: rgb(239 246 255 / 70%);
}

.page-dark .paper-card--active {
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

.question-surface-card--light {
  border-color: #e2e8f0;
  background: white;
}

.question-surface-card--dark {
  border-color: rgb(71 85 105 / 55%);
  background: rgb(15 23 42 / 92%);
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
