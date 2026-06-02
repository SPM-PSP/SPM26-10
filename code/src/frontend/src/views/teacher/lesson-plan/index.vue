<!-- eslint-disable vue/no-v-html -->
<template>
  <div :class="['h-full', theme.darkMode ? 'page-dark' : 'page-light']">
    <n-space vertical :size="20">
      <n-card title="教学计划生成" :bordered="false" class="rounded-8px shadow-sm">
        <div class="pb-12px text-16px">通过课程大纲、课程级别及预计课时生成教学计划，并可继续人工修改或基于意见二次润色。</div>
        <n-form ref="formRef" :model="courseData" :rules="courseDataRules" size="large" :show-label="true">
          <n-form-item label="课程大纲" path="course_outline">
            <n-input v-model:value="courseData.course_outline" placeholder="请输入课程大纲" />
          </n-form-item>
          <n-grid cols="1 l:2" responsive="screen" :x-gap="16">
            <n-grid-item>
              <n-form-item label="课程等级" path="course_level">
                <n-input v-model:value="courseData.course_level" placeholder="例如：大学三年级" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="预计课时" path="expected_duration_hours">
                <n-select v-model:value="courseData.expected_duration_hours" :options="hoursOptions" filterable />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-button type="primary" size="large" :loading="isLoading" @click="handleSubmit">
            {{ isLoading ? '生成中...' : '生成教学计划' }}
          </n-button>
        </n-form>
      </n-card>

      <n-grid cols="1 l:2" responsive="screen" :x-gap="16" :y-gap="16">
        <n-grid-item>
          <n-card title="教学计划列表" :bordered="false" class="rounded-8px shadow-sm">
            <n-space justify="space-between" align="center">
              <div class="text-14px text-#64748b">这里只显示当前教师自己生成的教学计划。</div>
              <n-button @click="fetchLessonPlans">刷新</n-button>
            </n-space>

            <n-space vertical :size="12" class="mt-16px">
              <template v-if="lessonPlans.length">
                <n-card
                  v-for="item in lessonPlans"
                  :key="item.id"
                  :bordered="false"
                  :class="['rounded-8px plan-card', selectedPlan?.id === item.id ? 'plan-card--active' : '']"
                  hoverable
                  @click="selectPlan(item.id)"
                >
                  <n-space vertical :size="8">
                    <div class="text-17px font-600">{{ item.title }}</div>
                    <div class="text-13px text-#64748b">创建时间：{{ formatDate(item.created_at) }}</div>
                    <div class="text-13px text-#64748b line-clamp-2">
                      {{ item.metadata_json?.course_level || '未标注级别' }} ｜ {{ item.metadata_json?.expected_duration_hours || '未标注课时' }} 课时
                    </div>
                    <n-space :size="10">
                      <n-button size="small" @click.stop="selectPlan(item.id)">查看/编辑</n-button>
                      <n-popconfirm @positive-click="deletePlan(item.id)">
                        <template #trigger>
                          <n-button size="small" type="error" ghost @click.stop>删除</n-button>
                        </template>
                        删除后将无法再用于生成试卷，确认继续？
                      </n-popconfirm>
                    </n-space>
                  </n-space>
                </n-card>
              </template>
              <template v-else>
                <n-empty description="还没有教学计划。" />
              </template>
            </n-space>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="教学计划编辑与二次修改" :bordered="false" class="rounded-8px shadow-sm">
            <template v-if="selectedPlan">
              <n-space vertical :size="16">
                <n-input v-model:value="editForm.title" placeholder="教学计划标题" />
                <n-input
                  v-model:value="editForm.content"
                  type="textarea"
                  :autosize="{ minRows: 14, maxRows: 28 }"
                  placeholder="在这里手动修改教学计划 Markdown 内容"
                />
                <n-space :size="12">
                  <n-button type="primary" :loading="saving" @click="savePlan">保存修改</n-button>
                  <n-button @click="previewMode = !previewMode">
                    {{ previewMode ? '返回编辑' : '预览 Markdown' }}
                  </n-button>
                </n-space>

                <n-card
                  v-if="previewMode"
                  title="预览"
                  :bordered="false"
                  :class="['rounded-8px editor-surface-card', theme.darkMode ? 'editor-surface-card--dark' : 'editor-surface-card--light']"
                >
                  <div class="markdown-body" v-html="editHtml"></div>
                </n-card>

                <n-card
                  title="AI 二次修改"
                  :bordered="false"
                  :class="['rounded-8px editor-surface-card', theme.darkMode ? 'editor-surface-card--dark' : 'editor-surface-card--light']"
                >
                  <n-space vertical :size="12">
                    <n-input
                      v-model:value="reviseInstruction"
                      type="textarea"
                      :autosize="{ minRows: 3, maxRows: 6 }"
                      placeholder="例如：请把实验部分再细化，并把总课时压缩到 6 课时"
                    />
                    <n-checkbox v-model:checked="saveAsNew">另存为新版本</n-checkbox>
                    <n-button type="warning" :loading="revising" @click="revisePlan">让模型继续修改</n-button>
                  </n-space>
                </n-card>
              </n-space>
            </template>
            <template v-else>
              <n-empty description="选择一份教学计划后，这里可以继续编辑或让模型按意见修改。" />
            </template>
          </n-card>
        </n-grid-item>
      </n-grid>

      <n-card title="最新生成结果" :bordered="false" class="rounded-8px shadow-sm">
        <template v-if="isLoading || lessonPlanContent">
          <pre v-if="isLoading" class="streaming-plain-text">{{ lessonPlanContent || '正在生成教学计划，请稍候...' }}</pre>
          <div v-else class="markdown-body" v-html="lessonPlanHtml"></div>
        </template>
        <template v-else>
          <n-empty description="生成新的教学计划后，这里会显示最新结果。" />
        </template>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import type { FormInst } from 'naive-ui';
import { marked } from 'marked';
import { useThemeStore } from '@/store';
import { formRules } from '@/utils';
import _axios from '@/utils/request';
import type { CourseOutlineInfo } from '@/types/document';

interface LessonPlanItem {
  id: string;
  title: string;
  created_by_user_id: number;
  created_at: string;
  metadata_json?: Record<string, any> | null;
  subject?: string | null;
  content: string;
}

const formRef = ref<HTMLElement & FormInst>();
const theme = useThemeStore();
const isLoading = ref(false);
const saving = ref(false);
const revising = ref(false);
const previewMode = ref(false);
const lessonPlanContent = ref<string | null>(null);
const lessonPlans = ref<LessonPlanItem[]>([]);
const selectedPlan = ref<LessonPlanItem | null>(null);
const reviseInstruction = ref('');
const saveAsNew = ref(false);

const lessonPlanHtml = computed(() => (lessonPlanContent.value ? marked.parse(lessonPlanContent.value) : ''));
const editHtml = computed(() => marked.parse(editForm.content || ''));

const courseData = reactive<CourseOutlineInfo>({
  course_outline: '',
  course_level: '',
  expected_duration_hours: null
});

const editForm = reactive({
  title: '',
  content: ''
});

const hoursOptions = Array.from({ length: 99 }, (_, i) => ({
  label: `${i + 1}课时`,
  value: i + 1
}));

const courseDataRules = {
  course_outline: formRules.course_outline,
  course_level: formRules.course_level,
  expected_duration_hours: formRules.expected_duration_hours
};

const BASE_URL = import.meta.env.VITE_APP_BASE_URL || 'http://127.0.0.1:8000';

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN');
}

async function fetchLessonPlans() {
  try {
    const response = await _axios.get<LessonPlanItem[]>('/api/teacher/lesson-plans');
    lessonPlans.value = response.data;
    if (selectedPlan.value) {
      const latest = lessonPlans.value.find(item => item.id === selectedPlan.value?.id);
      if (latest) {
        selectedPlan.value = latest;
        editForm.title = latest.title;
        editForm.content = latest.content;
      }
    }
  } catch (error: any) {
    console.error('加载教学计划列表失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载教学计划列表失败');
  }
}

async function selectPlan(id: string) {
  try {
    const response = await _axios.get<LessonPlanItem>(`/api/teacher/lesson-plans/${id}`);
    selectedPlan.value = response.data;
    editForm.title = response.data.title;
    editForm.content = response.data.content;
    previewMode.value = false;
  } catch (error: any) {
    console.error('加载教学计划详情失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载教学计划详情失败');
  }
}

async function savePlan() {
  if (!selectedPlan.value) return;
  try {
    saving.value = true;
    const response = await _axios.put<LessonPlanItem>(`/api/teacher/lesson-plans/${selectedPlan.value.id}`, {
      title: editForm.title,
      content: editForm.content
    });
    selectedPlan.value = response.data;
    lessonPlanContent.value = response.data.content;
    await fetchLessonPlans();
    window.$message?.success('教学计划已保存');
  } catch (error: any) {
    console.error('保存教学计划失败:', error);
    window.$message?.error(error?.response?.data?.detail || '保存教学计划失败');
  } finally {
    saving.value = false;
  }
}

async function revisePlan() {
  if (!selectedPlan.value || !reviseInstruction.value.trim()) {
    window.$message?.warning('请输入修改意见');
    return;
  }
  const saveAsNewSnapshot = saveAsNew.value;
  try {
    revising.value = true;
    const response = await _axios.post<LessonPlanItem>(`/api/teacher/lesson-plans/${selectedPlan.value.id}/revise`, {
      revision_instruction: reviseInstruction.value.trim(),
      save_as_new: saveAsNewSnapshot
    });
    lessonPlanContent.value = response.data.content;
    reviseInstruction.value = '';
    saveAsNew.value = false;
    if (response.data.id !== selectedPlan.value.id) {
      selectedPlan.value = response.data;
    } else {
      selectedPlan.value = response.data;
    }
    editForm.title = response.data.title;
    editForm.content = response.data.content;
    await fetchLessonPlans();
    window.$message?.success(saveAsNewSnapshot ? '已生成新的修订版教学计划' : '教学计划已按意见更新');
  } catch (error: any) {
    console.error('AI 修改教学计划失败:', error);
    window.$message?.error(error?.response?.data?.detail || 'AI 修改教学计划失败');
  } finally {
    revising.value = false;
  }
}

async function deletePlan(id: string) {
  try {
    await _axios.delete(`/api/teacher/lesson-plans/${id}`);
    if (selectedPlan.value?.id === id) {
      selectedPlan.value = null;
      editForm.title = '';
      editForm.content = '';
    }
    await fetchLessonPlans();
    window.$message?.success('教学计划删除成功');
  } catch (error: any) {
    console.error('删除教学计划失败:', error);
    window.$message?.error(error?.response?.data?.detail || '删除教学计划失败');
  }
}

const handleSubmit = async () => {
  try {
    isLoading.value = true;
    await formRef.value?.validate();

    const requestPayload: CourseOutlineInfo = {
      course_outline: courseData.course_outline,
      course_level: courseData.course_level,
      expected_duration_hours: typeof courseData.expected_duration_hours === 'number' ? courseData.expected_duration_hours : 0
    };

    lessonPlanContent.value = '';
    const sessionId = sessionStorage.getItem('session_id') || '';
    const response = await fetch(`${BASE_URL}/api/teacher/lesson_plan/generate/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId
      },
      body: JSON.stringify(requestPayload)
    });

    if (!response.ok || !response.body) {
      const message = await response.text();
      throw new Error(message || '教学计划生成失败');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      fullText += chunk;
      lessonPlanContent.value = fullText;
    }

    if (fullText.trim()) {
      window.$message?.success('教学计划生成成功');
      await fetchLessonPlans();
      if (lessonPlans.value.length) {
        await selectPlan(lessonPlans.value[0].id);
      }
    } else {
      lessonPlanContent.value = null;
      window.$message?.error('教学计划生成失败');
    }
  } catch (error: any) {
    console.error('生成教学计划失败:', error);
    window.$message?.error(error?.response?.data?.detail || error?.message || '请检查表单填写或网络状况');
    lessonPlanContent.value = null;
  } finally {
    isLoading.value = false;
  }
};

onMounted(fetchLessonPlans);
</script>

<style scoped>
.page-dark :deep(.n-card) {
  color: #e5e7eb;
}

.plan-card {
  cursor: pointer;
}

.plan-card--active {
  outline: 1px solid rgb(59 130 246 / 45%);
  background: rgb(239 246 255 / 70%);
}

.page-dark .plan-card--active {
  background: rgb(30 41 59 / 88%);
}

.editor-surface-card--light {
  background: #f8fafc;
}

.editor-surface-card--dark {
  background: rgb(30 41 59 / 82%);
  border: 1px solid rgb(71 85 105 / 45%);
}

.streaming-plain-text {
  white-space: pre-wrap;
  line-height: 1.75;
  color: inherit;
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
