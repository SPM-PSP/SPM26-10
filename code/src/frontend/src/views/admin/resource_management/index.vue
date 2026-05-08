<template>
  <div class="h-full overflow-hidden">
    <n-card title="资源管理" :bordered="false" class="h-full rounded-8px shadow-sm">
      <n-space vertical :size="20">
        <n-space justify="end">
          <n-button type="primary" :loading="loading" @click="fetchResources">
            加载数据
          </n-button>
          <n-button @click="clearResources">清空数据</n-button>
        </n-space>

        <loading-empty-wrapper class="h-480px" :loading="loading" :empty="empty">
          <n-data-table
            :columns="columns"
            :data="dataSource"
            :flex-height="true"
            class="h-480px"
            :scroll-x="1200"
            striped
          />
        </loading-empty-wrapper>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { h, ref } from 'vue';
import { NTag } from 'naive-ui';
import type { DataTableColumns } from 'naive-ui';
import _axios from '@/utils/request';

interface ResourceItem {
  id: string;
  title: string;
  resource_type: 'lesson_plan' | 'assessment' | 'practice';
  created_by_user_id: number;
  created_at: string;
  file_path: string;
  metadata_json: Record<string, any>;
  subject?: string | null;
}

const loading = ref(false);
const empty = ref(true);
const dataSource = ref<ResourceItem[]>([]);

function formatResourceType(type: ResourceItem['resource_type']) {
  const map: Record<ResourceItem['resource_type'], string> = {
    lesson_plan: '教案',
    assessment: '测验',
    practice: '练习'
  };

  return map[type];
}

function formatMetadata(item: ResourceItem) {
  const meta = item.metadata_json ?? {};

  switch (item.resource_type) {
    case 'lesson_plan':
      return `课程级别: ${meta.course_level || '无'}，课时: ${meta.expected_duration_hours || '0'}小时`;
    case 'assessment':
      return `题目数: ${meta.num_questions || '0'}，类型: ${meta.question_type || '未知'}，难度: ${meta.difficulty_level || '未知'}`;
    case 'practice':
      return `学生ID: ${meta.student_id || '未知'}，主题: ${meta.topic_focus || '无'}，题目数: ${meta.num_questions || '0'}`;
    default:
      return JSON.stringify(meta);
  }
}

const columns: DataTableColumns<ResourceItem> = [
  {
    title: '标题',
    key: 'title',
    width: 220,
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: '资源类型',
    key: 'resource_type',
    width: 120,
    render: row =>
      h(
        NTag,
        {
          bordered: false,
          type:
            row.resource_type === 'lesson_plan'
              ? 'success'
              : row.resource_type === 'assessment'
                ? 'warning'
                : 'info'
        },
        { default: () => formatResourceType(row.resource_type) }
      )
  },
  {
    title: '学科/主题',
    key: 'subject',
    width: 140,
    render: row => row.subject || '未设置'
  },
  {
    title: '创建者ID',
    key: 'created_by_user_id',
    width: 100
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render: row => new Date(row.created_at).toLocaleString()
  },
  {
    title: '元数据摘要',
    key: 'metadata_summary',
    width: 320,
    render: row => formatMetadata(row)
  },
  {
    title: '文件路径',
    key: 'file_path',
    minWidth: 260,
    ellipsis: {
      tooltip: true
    }
  }
];

async function fetchResources() {
  loading.value = true;

  try {
    const response = await _axios.get<ResourceItem[]>('/api/admin/resources');
    dataSource.value = Array.isArray(response.data) ? response.data : [];
    empty.value = dataSource.value.length === 0;
  } catch (error) {
    console.error('获取资源失败:', error);
    dataSource.value = [];
    empty.value = true;
  } finally {
    loading.value = false;
  }
}

function clearResources() {
  dataSource.value = [];
  empty.value = true;
}
</script>
