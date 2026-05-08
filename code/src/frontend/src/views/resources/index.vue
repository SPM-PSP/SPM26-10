<template>
  <div class="h-full">
    <n-card title="资源导出" :bordered="false" class="rounded-8px shadow-sm">
      <div class="pb-12px text-16px">导出指定的课件和练习资源到指定格式</div>
      <n-space vertical>
        <n-form ref="formRef" :model="exportForm" :rules="rules" label-placement="left">
          <n-form-item label="导出格式" path="format">
            <n-select v-model:value="exportForm.format" :options="formatOptions" />
          </n-form-item>
          <n-form-item label="包含答案" path="includeAnswers">
            <n-switch v-model:value="exportForm.includeAnswers" />
          </n-form-item>
        </n-form>
        <n-button type="primary" :loading="isLoading" @click="handleExport">
          <template #icon>
            <n-icon>
              <download-icon />
            </n-icon>
          </template>
          导出选中资源
        </n-button>
        <div v-if="downloadUrl" class="mt-4">
          <n-alert type="success" title="导出成功">
            <a :href="downloadUrl" download="resources.pdf">点击下载资源包</a>
          </n-alert>
        </div>
      </n-space>
    </n-card>
  </div>
  <div class="h-full overflow-hidden">
    <n-card title="资源表格" :bordered="false" class="h-full rounded-8px shadow-sm">
      <n-space :vertical="true">
        <n-space>
          <n-button @click="getDataSource">有数据</n-button>
          <n-button @click="getEmptyDataSource">空数据</n-button>
        </n-space>
        <loading-empty-wrapper class="h-480px" :loading="loading" :empty="empty">
          <n-data-table
            :columns="columns"
            :data="dataSource"
            :flex-height="true"
            class="h-480px"
            :row-key="row => row.id"
            @update:checked-row-keys="handleCheck"
          />
        </loading-empty-wrapper>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue';
import { NButton, NTag, NText } from 'naive-ui';
import type { FormInst, DataTableColumns } from 'naive-ui';
import { DownloadOutline as DownloadIcon } from '@vicons/ionicons5';
import html2pdf from 'html2pdf.js';

// 资源类型定义
interface Resource {
  id: string;
  title: string;
  resource_type: string;
  created_at: string;
  metadata_json: any;
}

// 表格相关状态
const formRef = ref<FormInst | null>(null);
const isLoading = ref(false);
const loading = ref(true);
const empty = ref(false);
const downloadUrl = ref('');
const checkedResourceIds = ref<string[]>([]);
const dataSource = ref<Resource[]>([]);

// 导出表单
const exportForm = reactive({
  format: 'pdf',
  includeAnswers: true
});

const formatOptions = [
  { label: 'PDF', value: 'pdf' },
  { label: 'Word', value: 'docx' },
  { label: 'Markdown', value: 'md' }
];

const rules = {
  format: [{ required: true, message: '请选择导出格式', trigger: 'blur' }]
};

// 表格列定义
const createColumns = (): DataTableColumns<Resource> => [
  {
    type: 'selection',
    fixed: 'left'
  },
  {
    title: '资源ID',
    key: 'id',
    width: 280,
    render(row: Resource) {
      return h(NText, { depth: 3 }, row.id);
    }
  },
  {
    title: '标题',
    key: 'title',
    minWidth: 200
  },
  {
    title: '类型',
    key: 'resource_type',
    width: 120,
    render(row: Resource) {
      const typeMap: Record<string, { color: string; text: string }> = {
        lesson_plan: { color: 'success', text: '课件' },
        assessment: { color: 'warning', text: '练习' },
        exercise: { color: 'info', text: '题目' }
      };
      const typeInfo = typeMap[row.resource_type] || { color: 'default', text: '未知' };
      return h(NTag, { type: typeInfo.color as any }, typeInfo.text);
    }
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180
  },
  {
    title: '元数据',
    key: 'metadata_json',
    render(row: Resource) {
      return JSON.stringify(row.metadata_json);
    }
  }
];

const columns = createColumns();

// 获取当前用户的资源
const fetchUserResources = async () => {
  try {
    loading.value = true;
    // 实际项目中替换为真实API调用
    const response = await fetch('/api/resources/user_resources', {
      headers: {
        'X-Session-ID': 'user-valid-session-id' // 替换为真实session ID
      }
    });
    const data = await response.json();
    dataSource.value = data;
    empty.value = data.length === 0;
  } catch (error) {
    /* eslint-disable no-console */
    console.error('获取资源失败:', error);
    empty.value = true;
  } finally {
    loading.value = false;
  }
};
// 生成PDF文件
const generatePDF = async (resources: Resource[]) => {
  const container = document.createElement('div');
  container.style.display = 'none';
  document.body.appendChild(container);

  // 渲染资源内容
  resources.forEach(resource => {
    const section = document.createElement('div');
    section.className = 'resource-section';

    const title = document.createElement('h2');
    title.textContent = resource.title;
    section.appendChild(title);

    const metaDiv = document.createElement('div');
    metaDiv.innerHTML = `
      <p><strong>资源ID:</strong> ${resource.id}</p>
      <p><strong>类型:</strong> ${resource.resource_type === 'lesson_plan' ? '课件' : '练习'}</p>
      <p><strong>创建时间:</strong> ${new Date(resource.created_at).toLocaleString()}</p>
    `;
    section.appendChild(metaDiv);

    // 这里实际应根据资源内容渲染
    const contentDiv = document.createElement('div');
    contentDiv.className = 'resource-content';
    contentDiv.innerHTML = `<p>这是 ${resource.title} 的详细内容...</p>`;
    section.appendChild(contentDiv);

    container.appendChild(section);
  });

  // 生成PDF
  const options = {
    margin: 10,
    filename: 'resources-export.pdf',
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2 },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
  };

  await html2pdf().set(options).from(container).save(); // 创建Blob URL用于下载
  const blob = await html2pdf().set(options).from(container).output('blob');
  const url = URL.createObjectURL(blob);

  // 清理
  document.body.removeChild(container);

  return url;
};
// 勾选框事件处理
const handleCheck = (rowKeys: (string | number)[]) => {
  checkedResourceIds.value = rowKeys.map(String); // 转换为字符串数组
};

// 导出资源处理
const handleExport = async () => {
  if (checkedResourceIds.value.length === 0) {
    window.$message?.warning('请至少选择一个资源');
    return;
  }

  try {
    isLoading.value = true;
    // 构建查询参数
    const queryParams = checkedResourceIds.value.map(id => `resource_ids=${id}`).join('&');
    // 调用导出API
    const response = await fetch(`/resources/content?${queryParams}`, {
      headers: {
        'X-Session-ID': 'user-valid-session-id' // 替换为真实session ID
      }
    });

    const resources = await response.json();

    // 生成PDF
    const pdfUrl = await generatePDF(resources);
    downloadUrl.value = pdfUrl;

    window.$message?.success('导出成功，请点击下载链接');
  } catch (error) {
    console.error('导出失败:', error);
    window.$message?.error('导出失败，请重试');
  } finally {
    isLoading.value = false;
  }
};

// 模拟数据方法
const getDataSource = () => {
  dataSource.value = [
    {
      id: '01f76e0c-d3e4-4f89-86d8-a406687b89a6',
      title: 'TensorFlow.js 的核心概念与环境配置',
      resource_type: 'lesson_plan',
      created_at: '2025-07-06T16:01:21',
      metadata_json: {
        course_level: '大学三年级',
        expected_duration_hours: 4
      }
    },
    {
      id: '49b2d890-1c73-433b-ae6a-ac211c60264f',
      title: 'TensorFlow Lite 模型转换-选择题-中等',
      resource_type: 'assessment',
      created_at: '2025-07-08T10:48:08',
      metadata_json: {
        num_questions: 2,
        question_type: '选择题',
        difficulty_level: '中等',
        programming_language: null
      }
    }
  ];
  empty.value = false;
};

const getEmptyDataSource = () => {
  dataSource.value = [];
  empty.value = true;
};

// 初始化加载数据
onMounted(() => {
  fetchUserResources();
});
</script>
