<template>
  <div class="overflow-hidden h-full">
    <n-card title="教师资源列表" :bordered="false" class="h-full rounded-8px shadow-sm">
      <n-space vertical :size="20">
        <n-space justify="end">
          <n-button size="small" type="primary" :loading="loading" @click="fetchResources">
            <icon-mdi-refresh class="mr-4px text-16px" :class="{ 'animate-spin': loading }" />
            刷新资源
          </n-button>
        </n-space>

        <n-data-table
          :columns="columns"
          :data="resources"
          :loading="loading"
          :pagination="pagination"
          :row-key="rowKey"
          flex-height
          class="flex-1-hidden"
          remote
          style="height: 400px"
        />

        <n-alert v-if="errorMsg" type="error" title="数据加载失败">
          {{ errorMsg }}
        </n-alert>
      </n-space>
    </n-card>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, reactive, h } from 'vue'; // 引入 h 用于 JSX 渲染
import type { Ref } from 'vue';
import { NTag, NSpace, NButton } from 'naive-ui';
import type { DataTableColumns, PaginationProps } from 'naive-ui';
import { useLoading } from '@/hooks';
import _axios from '@/utils/request'; // 假设您使用这个 axios 实例
import type { TeacherResource, ResourceType } from '@/types/resource'; // 引入新的类型定义

const { loading, startLoading, endLoading } = useLoading(false);
const resources = ref<TeacherResource[]>([]);
const errorMsg = ref<string | null>(null);

// 资源类型标签的颜色映射
const resourceTypeTagMap: Record<ResourceType, NaiveUI.ThemeColor> = {
  assessment: 'error',
  practice: 'info',
  lesson_plan: 'success'
};

// 分页配置
const pagination: PaginationProps = reactive({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 15, 20, 25, 30],
  itemCount: 0, // 后端通常会返回总数，这里需要更新
  onChange: (page: number) => {
    pagination.page = page;
    fetchResources(); // 页码改变时重新获取数据
  },
  onUpdatePageSize: (pageSize: number) => {
    pagination.pageSize = pageSize;
    pagination.page = 1; // 改变每页大小时回到第一页
    fetchResources(); // 每页大小改变时重新获取数据
  }
});

/**
 * 获取教师资源列表
 */
async function fetchResources() {
  startLoading();
  errorMsg.value = null;

  try {
    const response = await _axios.get<TeacherResource[]>('/api/admin/resources');

    // eslint-disable-next-line no-console
    console.log('API原始响应数据:', response.data); // 添加这一行来查看原始数据

    if (response.data && Array.isArray(response.data)) {
      // 确保data是数组
      resources.value = response.data; // 直接赋值，序号在 render 中计算
      pagination.itemCount = response.data.length;
      // eslint-disable-next-line no-console
      console.log('resources.value (赋值后):', resources.value); // 添加这一行来确认ref的值
    } else {
      resources.value = [];
      pagination.itemCount = 0;
      // eslint-disable-next-line no-console
      console.log('未获取到教师资源数据或数据为空。');
    }
    window.$message?.success('资源加载成功！');
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Failed to fetch resources:', error);
    // ... (错误处理)
  } finally {
    endLoading();
  }
}

// 定义表格列
const columns: Ref<DataTableColumns<TeacherResource>> = ref([
  {
    key: 'index',
    title: '序号',
    align: 'center',
    width: 60,
    // 使用 render 函数的第二个参数 index 来计算当前页的序号
    render: (_row, index) => {
      // 确保 pagination.page 和 pagination.pageSize 不为 undefined，虽然这里逻辑上它们总是被初始化了
      return (pagination.page! - 1) * pagination.pageSize! + index + 1;
    }
  },
  {
    key: 'title',
    title: '标题',
    align: 'left',
    minWidth: 180
  },
  {
    key: 'resource_type',
    title: '资源类型',
    align: 'center',
    width: 120,
    render: row => {
      // 使用 NTag 美化显示
      return h(
        NTag,
        { type: resourceTypeTagMap[row.resource_type], bordered: false },
        {
          default: () => {
            // 将 resource_type 转换为中文显示
            switch (row.resource_type) {
              case 'assessment':
                return '测评';
              case 'practice':
                return '练习';
              case 'lesson_plan':
                return '教案';
              default:
                return row.resource_type;
            }
          }
        }
      );
    }
  },
  {
    key: 'subject',
    title: '科目',
    align: 'center',
    width: 120,
    render: row => row.subject || 'N/A' // 如果subject为null显示N/A
  },
  {
    key: 'created_by_user_id',
    title: '创建者ID',
    align: 'center',
    width: 100
  },
  {
    key: 'created_at',
    title: '创建时间',
    align: 'center',
    width: 180,
    render: row => {
      // 格式化时间显示
      const date = new Date(row.created_at);
      return date.toLocaleString();
    }
  },
  {
    key: 'metadata_json',
    title: '元数据',
    align: 'left',
    minWidth: 200,
    render: row => {
      // 动态渲染 metadata_json 的内容
      const metadata = row.metadata_json;
      if (!metadata || Object.keys(metadata).length === 0) {
        return h('span', {}, '无');
      }

      const elements: any[] = [];
      for (const key in metadata) {
        // 使用 Object.prototype.hasOwnProperty.call 而不是 Object.hasOwn 兼容性更好
        if (Object.hasOwn(metadata, key)) {
          let displayKey = '';
          const displayValue = metadata[key];

          // 根据 key 转换为更友好的中文显示
          switch (key) {
            case 'num_questions':
              displayKey = '题目数';
              break;
            case 'question_type':
              displayKey = '题目类型';
              break;
            case 'difficulty_level':
              displayKey = '难度';
              break;
            case 'programming_language':
              displayKey = '编程语言';
              break;
            case 'student_id':
              displayKey = '学生ID';
              break;
            case 'topic_focus':
              displayKey = '主题';
              break;
            case 'course_level':
              displayKey = '课程级别';
              break;
            case 'expected_duration_hours':
              displayKey = '预计时长(小时)';
              break;
            default:
              displayKey = key;
              break;
          }

          elements.push(h('div', {}, `${displayKey}: ${displayValue}`));
        }
      }
      return h(NSpace, { vertical: true, size: 0 }, { default: () => elements });
    }
  },
  // 可以根据需要添加更多操作列，如查看详情、下载等
  {
    key: 'actions',
    title: '操作',
    align: 'center',
    width: 120,
    render: row => {
      return h(NSpace, { justify: 'center' }, [
        h(NButton, { size: 'small', onClick: () => handleViewDetails(row) }, { default: () => '查看详情' })
        // 可以添加下载按钮等
      ]);
    }
  }
]) as Ref<DataTableColumns<TeacherResource>>;

function rowKey(rowData: TeacherResource) {
  return rowData.id;
}

function handleViewDetails(row: TeacherResource) {
  window.$message?.info(`查看资源详情：${row.title}`);
  // 实际项目中，这里可以导航到详情页，或者弹出模态框显示更多信息
  // eslint-disable-next-line no-console
  console.log('Resource details:', row);
  // 示例：打开文件路径（需要后端提供可访问的静态文件服务）
  // if (row.file_path) {
  //   window.open(`/${row.file_path}`, '_blank');
  // }
}

// 组件挂载时获取数据
onMounted(() => {
  fetchResources();
});
</script>
<style scoped>
.h-full {
  height: 100%;
}
.overflow-hidden {
  overflow: hidden;
}
.flex-1-hidden {
  flex: 1;
  min-height: 0; /* 确保在 flex 布局中可以隐藏溢出 */
}
</style>
