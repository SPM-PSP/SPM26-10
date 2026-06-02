<template>
  <div :class="['h-full', theme.darkMode ? 'page-dark' : 'page-light']">
    <n-space vertical :size="20">
      <n-card title="从教学计划生成试卷" :bordered="false" class="rounded-8px shadow-sm">
        <div class="pb-12px text-16px">仅展示你自己生成的教学计划。生成后可继续编辑、追加已生成考核题，并发布到班级。</div>
        <n-form ref="generateFormRef" :model="generateForm" :rules="generateRules" size="large" label-placement="left">
          <n-grid cols="1 l:3" responsive="screen" :x-gap="16" :y-gap="8">
            <n-grid-item>
              <n-form-item label="教学计划" path="source_resource_id">
                <n-select
                  v-model:value="generateForm.source_resource_id"
                  :options="lessonPlanOptions"
                  placeholder="请选择教学计划"
                />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="试卷标题" path="title">
                <n-input v-model:value="generateForm.title" placeholder="例如：第1章阶段测试" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="题型" path="question_type">
                <n-select v-model:value="generateForm.question_type" :options="generationQuestionTypeOptions" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="难度" path="difficulty_level">
                <n-select v-model:value="generateForm.difficulty_level" :options="difficultyOptions" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="每模块题数" path="questions_per_section">
                <n-input-number v-model:value="generateForm.questions_per_section" class="w-full" :min="1" :max="10" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="最多模块数" path="max_sections">
                <n-input-number v-model:value="generateForm.max_sections" class="w-full" :min="1" :max="12" />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-space>
            <n-button type="primary" :loading="generating" @click="generatePaper">生成试卷草稿</n-button>
            <n-button @click="refreshBaseData">刷新教学计划/班级/考核题</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-grid cols="1 l:2" responsive="screen" :x-gap="16" :y-gap="16">
        <n-grid-item>
          <n-card title="试卷列表" :bordered="false" class="rounded-8px shadow-sm">
            <n-space vertical :size="12">
              <div class="text-14px text-#64748b">草稿试卷可继续编辑，已发布试卷可归档保留历史数据。</div>
              <n-button @click="fetchPapers">刷新试卷列表</n-button>
              <template v-if="papers.length">
                <n-card
                  v-for="paper in papers"
                  :key="paper.id"
                  :bordered="false"
                  :class="['rounded-8px paper-card', selectedPaper?.id === paper.id ? 'paper-card--active' : '']"
                  hoverable
                  @click="selectPaper(paper.id)"
                >
                  <n-space vertical :size="8">
                    <div class="text-17px font-600">{{ paper.title }}</div>
                    <div class="text-13px text-#64748b">状态：{{ paper.status }} ｜ 总分：{{ paper.total_score }}</div>
                    <div class="text-13px text-#64748b">发布次数：{{ paper.publication_count }}</div>
                    <n-space :size="10">
                      <n-button size="small" @click.stop="selectPaper(paper.id)">查看</n-button>
                      <n-popconfirm @positive-click="deletePaper(paper)">
                        <template #trigger>
                          <n-button size="small" type="error" ghost @click.stop>
                            {{ paper.publication_count > 0 ? '归档' : '删除' }}
                          </n-button>
                        </template>
                        {{ paper.publication_count > 0 ? '该试卷已发布，归档后学生将不再看到新入口。确认继续？' : '确认删除这份试卷草稿？' }}
                      </n-popconfirm>
                    </n-space>
                  </n-space>
                </n-card>
              </template>
              <template v-else>
                <n-empty description="还没有试卷草稿。" />
              </template>
            </n-space>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="试卷编辑与发布" :bordered="false" class="rounded-8px shadow-sm">
            <template v-if="selectedPaper">
              <n-space vertical :size="16">
                <n-tag :type="selectedPaper.status === 'draft' ? 'info' : selectedPaper.status === 'published' ? 'success' : 'warning'" round>
                  当前状态：{{ selectedPaper.status }}
                </n-tag>
                <n-input v-model:value="selectedPaper.title" placeholder="试卷标题" />

                <n-card :bordered="false" :class="['rounded-8px editor-surface-card', theme.darkMode ? 'editor-surface-card--dark' : 'editor-surface-card--light']">
                  <template #header>追加已生成考核题</template>
                  <n-grid cols="1 l:3" responsive="screen" :x-gap="12" :y-gap="8">
                    <n-grid-item>
                      <n-select
                        v-model:value="appendForm.resource_id"
                        :options="generatedAssessmentOptions"
                        placeholder="选择已生成考核题"
                      />
                    </n-grid-item>
                    <n-grid-item>
                      <n-input v-model:value="appendForm.section_title" placeholder="追加后模块标题（可选）" />
                    </n-grid-item>
                    <n-grid-item>
                      <n-button type="primary" secondary :loading="appendingQuestions" @click="appendGeneratedQuestions">
                        追加到当前试卷
                      </n-button>
                    </n-grid-item>
                  </n-grid>
                </n-card>

                <n-card
                  v-for="section in selectedPaper.sections"
                  :key="section.id"
                  :bordered="false"
                  :class="['rounded-8px editor-surface-card', theme.darkMode ? 'editor-surface-card--dark' : 'editor-surface-card--light']"
                >
                  <n-space vertical :size="12">
                    <n-grid cols="1 l:2" responsive="screen" :x-gap="12">
                      <n-grid-item>
                        <n-input v-model:value="section.section_title" placeholder="模块标题" />
                      </n-grid-item>
                      <n-grid-item>
                        <n-input v-model:value="section.source_module_name" placeholder="来源模块名称（可选）" />
                      </n-grid-item>
                    </n-grid>

                    <div
                      v-for="question in section.questions"
                      :key="question.id"
                        :class="['rounded-8px border border-solid p-14px question-surface-card', theme.darkMode ? 'question-surface-card--dark' : 'question-surface-card--light']"
                      >
                      <n-space vertical :size="10">
                        <n-input
                          v-model:value="question.question_content"
                          type="textarea"
                          :autosize="{ minRows: 3, maxRows: 8 }"
                          placeholder="题目内容"
                        />
                        <n-grid cols="1 l:3" responsive="screen" :x-gap="12">
                          <n-grid-item>
                            <n-select v-model:value="question.question_type" :options="concreteQuestionTypeOptions" />
                          </n-grid-item>
                          <n-grid-item>
                            <n-select v-model:value="question.difficulty_level" :options="difficultyOptions" />
                          </n-grid-item>
                          <n-grid-item>
                            <n-input-number v-model:value="question.score" class="w-full" :min="1" :max="100" />
                          </n-grid-item>
                        </n-grid>

                        <n-dynamic-input
                          v-if="question.question_type === '选择题'"
                          v-model:value="question.metadata_json.options"
                          :min="2"
                          show-sort-button
                        >
                          <template #default="{ value, index }">
                            <n-input
                              :value="value"
                              placeholder="请输入选项内容"
                              @update:value="newValue => question.metadata_json.options[index] = newValue"
                            />
                          </template>
                        </n-dynamic-input>

                        <n-input
                          v-model:value="question.reference_answer"
                          type="textarea"
                          :autosize="{ minRows: 2, maxRows: 6 }"
                          placeholder="参考答案"
                        />
                      </n-space>
                    </div>
                  </n-space>
                </n-card>

                <n-space wrap>
                  <n-button type="primary" :loading="saving" @click="savePaper">保存试卷</n-button>
                  <n-select
                    v-model:value="publishForm.class_id"
                    class="w-240px"
                    :options="classOptions"
                    placeholder="选择发布班级"
                  />
                  <n-date-picker
                    v-model:value="publishForm.deadline"
                    class="w-260px"
                    type="datetime"
                    clearable
                    placeholder="设置截止时间"
                  />
                  <n-button type="success" :loading="publishing" @click="publishPaper">发布到班级</n-button>
                </n-space>
              </n-space>
            </template>
            <template v-else>
              <n-empty description="请先生成或选择一份试卷。" />
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
import { createRequiredFormRule } from '@/utils/form/rule';
import { useThemeStore } from '@/store';
import _axios from '@/utils/request';
import type { GeneratedQuestionSet } from '@/types/assessment';

defineOptions({ name: 'TeacherPapersPage' });
const theme = useThemeStore();

interface ResourceItem {
  id: string;
  title: string;
  resource_type: 'lesson_plan' | 'assessment' | 'practice';
  created_by_user_id: number;
}

interface ClassItem {
  id: string;
  name: string;
  class_code: string;
  status: string;
}

interface PaperQuestion {
  id: string;
  question_type: '选择题' | '填空题' | '简答题' | '编程题';
  question_content: string;
  reference_answer?: string | null;
  score: number;
  difficulty_level?: string | null;
  sort_order: number;
  metadata_json: {
    options: string[];
    [key: string]: any;
  };
}

interface PaperSection {
  id: string;
  section_title: string;
  source_module_name?: string | null;
  sort_order: number;
  questions: PaperQuestion[];
}

interface PaperItem {
  id: string;
  title: string;
  status: string;
  total_score: number;
  publication_count: number;
  sections: PaperSection[];
}

const generateFormRef = ref<FormInst | null>(null);
const generating = ref(false);
const saving = ref(false);
const publishing = ref(false);
const appendingQuestions = ref(false);

const lessonPlanResources = ref<ResourceItem[]>([]);
const classes = ref<ClassItem[]>([]);
const papers = ref<PaperItem[]>([]);
const generatedAssessments = ref<GeneratedQuestionSet[]>([]);
const selectedPaper = ref<PaperItem | null>(null);

const generateForm = reactive({
  source_resource_id: '',
  title: '',
  question_type: '混合',
  difficulty_level: '中等',
  questions_per_section: 2,
  max_sections: 4
});

const publishForm = reactive<{
  class_id: string | null;
  deadline: number | null;
}>({
  class_id: null,
  deadline: null
});

const appendForm = reactive({
  resource_id: null as string | null,
  section_title: ''
});

const generateRules: FormRules = {
  source_resource_id: [createRequiredFormRule('请选择教学计划')],
  title: [createRequiredFormRule('请输入试卷标题')]
};

const generationQuestionTypeOptions = [
  { label: '混合', value: '混合' },
  { label: '选择题', value: '选择题' },
  { label: '填空题', value: '填空题' },
  { label: '简答题', value: '简答题' },
  { label: '编程题', value: '编程题' }
];

const concreteQuestionTypeOptions = generationQuestionTypeOptions.filter(item => item.value !== '混合');

const difficultyOptions = [
  { label: '简单', value: '简单' },
  { label: '中等', value: '中等' },
  { label: '困难', value: '困难' }
];

const lessonPlanOptions = computed(() =>
  lessonPlanResources.value.map(item => ({ label: item.title, value: item.id }))
);

const classOptions = computed(() =>
  classes.value
    .filter(item => item.status === 'active')
    .map(item => ({ label: `${item.name}（${item.class_code}）`, value: item.id }))
);

const generatedAssessmentOptions = computed(() =>
  generatedAssessments.value.map(item => ({ label: `${item.title}（${item.questions.length}题）`, value: item.id }))
);

function normalizePaperQuestion(question: any): PaperQuestion {
  return {
    ...question,
    question_type: question.question_type,
    question_content: question.question_content || '',
    reference_answer: question.reference_answer || '',
    score: Number(question.score || 0),
    difficulty_level: question.difficulty_level || '中等',
    sort_order: question.sort_order || 1,
    metadata_json: {
      ...(question.metadata_json || {}),
      options: Array.isArray(question.metadata_json?.options) ? [...question.metadata_json.options] : []
    }
  };
}

function normalizePaper(paper: PaperItem): PaperItem {
  return {
    ...paper,
    sections: (paper.sections || []).map(section => ({
      ...section,
      source_module_name: section.source_module_name || '',
      questions: (section.questions || []).map(normalizePaperQuestion)
    }))
  };
}

function clonePaper<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

async function fetchLessonPlans() {
  try {
    const response = await _axios.get<ResourceItem[]>('/api/teacher/resources', {
      params: { resource_type: 'lesson_plan' }
    });
    lessonPlanResources.value = response.data;
  } catch (error: any) {
    console.error('加载教学计划资源失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载教学计划资源失败');
  }
}

async function fetchClasses() {
  try {
    const response = await _axios.get<ClassItem[]>('/api/teacher/classes');
    classes.value = response.data;
  } catch (error: any) {
    console.error('加载班级失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载班级失败');
  }
}

async function fetchGeneratedAssessments() {
  try {
    const response = await _axios.get<GeneratedQuestionSet[]>('/api/teacher/generated-assessments');
    generatedAssessments.value = response.data;
  } catch (error: any) {
    console.error('加载已生成考核题失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载已生成考核题失败');
  }
}

async function fetchPapers() {
  try {
    const response = await _axios.get<PaperItem[]>('/api/teacher/papers');
    papers.value = response.data.map(normalizePaper);
    if (selectedPaper.value) {
      const latest = papers.value.find(item => item.id === selectedPaper.value?.id);
      if (latest) {
        selectedPaper.value = clonePaper(latest);
      }
    }
  } catch (error: any) {
    console.error('加载试卷列表失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载试卷列表失败');
  }
}

async function refreshBaseData() {
  await Promise.all([fetchLessonPlans(), fetchClasses(), fetchGeneratedAssessments()]);
}

async function selectPaper(paperId: string) {
  try {
    const response = await _axios.get<PaperItem>(`/api/teacher/papers/${paperId}`);
    selectedPaper.value = normalizePaper(response.data);
  } catch (error: any) {
    console.error('加载试卷详情失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载试卷详情失败');
  }
}

async function generatePaper() {
  try {
    await generateFormRef.value?.validate();
    generating.value = true;
    const response = await _axios.post<PaperItem>('/api/teacher/papers/from-lesson-plan', generateForm);
    window.$message?.success('试卷草稿生成成功');
    generateForm.title = '';
    await fetchPapers();
    await selectPaper(response.data.id);
  } catch (error: any) {
    console.error('生成试卷草稿失败:', error);
    window.$message?.error(error?.response?.data?.detail || '生成试卷草稿失败');
  } finally {
    generating.value = false;
  }
}

function buildPaperPayload() {
  if (!selectedPaper.value) return null;
  return {
    title: selectedPaper.value.title,
    status: selectedPaper.value.status,
    sections: selectedPaper.value.sections.map((section, sectionIndex) => ({
      id: section.id,
      section_title: section.section_title,
      source_module_name: section.source_module_name || null,
      sort_order: section.sort_order || sectionIndex + 1,
      questions: section.questions.map((question, questionIndex) => ({
        id: question.id,
        question_type: question.question_type,
        question_content: question.question_content,
        reference_answer: question.reference_answer || '',
        score: Number(question.score || 0),
        difficulty_level: question.difficulty_level || '中等',
        sort_order: question.sort_order || questionIndex + 1,
        metadata_json: {
          ...(question.metadata_json || {}),
          options: question.question_type === '选择题'
            ? (question.metadata_json?.options || []).filter(Boolean)
            : []
        }
      }))
    }))
  };
}

async function savePaper() {
  if (!selectedPaper.value) return;
  const payload = buildPaperPayload();
  if (!payload) return;
  try {
    saving.value = true;
    const response = await _axios.put<PaperItem>(`/api/teacher/papers/${selectedPaper.value.id}`, payload);
    selectedPaper.value = normalizePaper(response.data);
    await fetchPapers();
    window.$message?.success('试卷保存成功');
  } catch (error: any) {
    console.error('保存试卷失败:', error);
    window.$message?.error(error?.response?.data?.detail || '保存试卷失败');
  } finally {
    saving.value = false;
  }
}

async function appendGeneratedQuestions() {
  if (!selectedPaper.value) return;
  if (!appendForm.resource_id) {
    window.$message?.warning('请先选择一套已生成考核题');
    return;
  }
  try {
    appendingQuestions.value = true;
    const response = await _axios.post<PaperItem>(`/api/teacher/papers/${selectedPaper.value.id}/append-generated-questions`, {
      resource_id: appendForm.resource_id,
      section_title: appendForm.section_title || null
    });
    selectedPaper.value = normalizePaper(response.data);
    appendForm.resource_id = null;
    appendForm.section_title = '';
    await fetchPapers();
    window.$message?.success('考核题已追加到试卷');
  } catch (error: any) {
    console.error('追加考核题失败:', error);
    window.$message?.error(error?.response?.data?.detail || '追加考核题失败');
  } finally {
    appendingQuestions.value = false;
  }
}

async function publishPaper() {
  if (!selectedPaper.value) return;
  if (!publishForm.class_id) {
    window.$message?.warning('请先选择发布班级');
    return;
  }
  try {
    publishing.value = true;
    await _axios.post(`/api/teacher/papers/${selectedPaper.value.id}/publish`, {
      class_id: publishForm.class_id,
      deadline: publishForm.deadline ? new Date(publishForm.deadline).toISOString() : null
    });
    publishForm.class_id = null;
    publishForm.deadline = null;
    await fetchPapers();
    await selectPaper(selectedPaper.value.id);
    window.$message?.success('试卷发布成功');
  } catch (error: any) {
    console.error('发布试卷失败:', error);
    window.$message?.error(error?.response?.data?.detail || '发布试卷失败');
  } finally {
    publishing.value = false;
  }
}

async function deletePaper(paper: PaperItem) {
  try {
    await _axios.delete(`/api/teacher/papers/${paper.id}`);
    if (selectedPaper.value?.id === paper.id) {
      selectedPaper.value = null;
    }
    await fetchPapers();
    window.$message?.success(paper.publication_count > 0 ? '试卷已归档' : '试卷已删除');
  } catch (error: any) {
    console.error('删除/归档试卷失败:', error);
    window.$message?.error(error?.response?.data?.detail || '删除/归档试卷失败');
  }
}

onMounted(async () => {
  await refreshBaseData();
  await fetchPapers();
  if (papers.value.length) {
    await selectPaper(papers.value[0].id);
  }
});
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

.editor-surface-card--light {
  background: #f8fafc;
}

.editor-surface-card--dark {
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
</style>
