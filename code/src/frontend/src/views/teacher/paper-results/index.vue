<template>
  <div class="h-full">
    <n-space vertical :size="20">
      <n-card title="试卷结果分析" :bordered="false" class="rounded-8px shadow-sm">
        <n-space align="center" justify="space-between" wrap>
          <n-select
            v-model:value="selectedPaperId"
            class="w-320px"
            :options="paperOptions"
            placeholder="请选择试卷"
            @update:value="loadSubmissions"
          />
          <n-button @click="fetchPapers">刷新</n-button>
        </n-space>
      </n-card>

      <n-grid cols="1 l:2" responsive="screen" :x-gap="16" :y-gap="16">
        <n-grid-item>
          <n-card title="提交列表" :bordered="false" class="rounded-8px shadow-sm">
            <n-spin :show="loadingList">
              <template v-if="submissions.length">
                <n-data-table :columns="columns" :data="submissions" :pagination="{ pageSize: 8 }" />
              </template>
              <template v-else>
                <n-empty description="当前试卷还没有学生提交。" />
              </template>
            </n-spin>
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="单份批改详情" :bordered="false" class="rounded-8px shadow-sm">
            <n-spin :show="loadingDetail">
              <template v-if="selectedSubmission">
                <n-space vertical :size="14">
                  <div class="text-18px font-700">
                    {{ selectedSubmission.student_name }}：{{ selectedSubmission.total_score }} / {{ selectedSubmission.max_score }}
                  </div>
                  <div class="text-14px text-#64748b">
                    提交时间：{{ formatDate(selectedSubmission.submitted_at) }} ｜ 正确率：{{ formatPercentage(selectedSubmission.correctness_percentage) }}
                  </div>
                  <n-card
                    v-for="answer in selectedSubmission.answers"
                    :key="answer.id"
                    :bordered="false"
                    class="rounded-8px bg-#f8fafc"
                  >
                    <n-space vertical :size="8">
                      <div class="font-600">{{ answer.question_content }}</div>
                      <div class="text-13px text-#64748b">学生答案：{{ answer.student_answer || '未作答' }}</div>
                      <div class="text-13px text-#64748b">参考答案：{{ answer.reference_answer || '无' }}</div>
                      <div class="text-13px text-#0f766e">得分：{{ answer.score }} / {{ answer.max_score }}</div>
                      <div class="text-14px text-#334155 whitespace-pre-wrap">{{ answer.auto_feedback || '暂无反馈' }}</div>
                    </n-space>
                  </n-card>
                </n-space>
              </template>
              <template v-else>
                <n-empty description="从左侧提交列表选择一条记录后，这里会显示批改详情。" />
              </template>
            </n-spin>
          </n-card>
        </n-grid-item>
      </n-grid>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, ref } from 'vue';
import type { DataTableColumns } from 'naive-ui';
import _axios from '@/utils/request';

defineOptions({ name: 'TeacherPaperResultsPage' });

interface PaperItem {
  id: string;
  title: string;
}

interface SubmissionSummary {
  id: string;
  student_id: number;
  student_name: string;
  submitted_at: string;
  total_score: number;
  max_score: number;
  correctness_percentage?: number | null;
  status: string;
}

interface SubmissionAnswer {
  id: string;
  question_content: string;
  reference_answer?: string | null;
  student_answer: string;
  auto_feedback?: string | null;
  score: number;
  max_score: number;
}

interface SubmissionDetail extends SubmissionSummary {
  answers: SubmissionAnswer[];
}

const papers = ref<PaperItem[]>([]);
const selectedPaperId = ref<string | null>(null);
const submissions = ref<SubmissionSummary[]>([]);
const selectedSubmission = ref<SubmissionDetail | null>(null);
const loadingList = ref(false);
const loadingDetail = ref(false);

const paperOptions = ref<{ label: string; value: string }[]>([]);

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '未设置';
}

function formatPercentage(value?: number | null) {
  return `${Math.round((value || 0) * 100)}%`;
}

const columns: DataTableColumns<SubmissionSummary> = [
  { title: '学生', key: 'student_name' },
  {
    title: '得分',
    key: 'total_score',
    render: row => h('span', `${row.total_score} / ${row.max_score}`)
  },
  {
    title: '正确率',
    key: 'correctness_percentage',
    render: row => h('span', formatPercentage(row.correctness_percentage))
  },
  {
    title: '提交时间',
    key: 'submitted_at',
    render: row => h('span', formatDate(row.submitted_at))
  },
  {
    title: '查看',
    key: 'actions',
    render: row =>
      h(
        'button',
        {
          class: 'cursor-pointer border-none bg-transparent text-#2563eb',
          onClick: () => loadSubmissionDetail(row.id)
        },
        '查看详情'
      )
  }
];

async function fetchPapers() {
  try {
    const response = await _axios.get<PaperItem[]>('/api/teacher/papers');
    papers.value = response.data;
    paperOptions.value = response.data.map(item => ({ label: item.title, value: item.id }));
    if (!selectedPaperId.value && response.data.length) {
      selectedPaperId.value = response.data[0].id;
      await loadSubmissions();
    }
  } catch (error: any) {
    console.error('加载试卷列表失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载试卷列表失败');
  }
}

async function loadSubmissions() {
  if (!selectedPaperId.value) return;
  loadingList.value = true;
  selectedSubmission.value = null;
  try {
    const response = await _axios.get<SubmissionSummary[]>(`/api/teacher/papers/${selectedPaperId.value}/submissions`);
    submissions.value = response.data;
  } catch (error: any) {
    console.error('加载提交列表失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载提交列表失败');
  } finally {
    loadingList.value = false;
  }
}

async function loadSubmissionDetail(submissionId: string) {
  loadingDetail.value = true;
  try {
    const response = await _axios.get<SubmissionDetail>(`/api/teacher/submissions/${submissionId}`);
    selectedSubmission.value = response.data;
  } catch (error: any) {
    console.error('加载提交详情失败:', error);
    window.$message?.error(error?.response?.data?.detail || '加载提交详情失败');
  } finally {
    loadingDetail.value = false;
  }
}

onMounted(fetchPapers);
</script>
