<template>
  <div class="overflow-hidden h-full">
    <n-card title="用户账户列表" :bordered="false" class="h-full rounded-8px shadow-sm">
      <n-space vertical :size="20">
        <n-space justify="end">
          <n-button size="small" type="primary" :loading="loading" @click="fetchUserAccounts">
            <icon-mdi-refresh class="mr-4px text-16px" :class="{ 'animate-spin': loading }" />
            刷新列表
          </n-button>
        </n-space>

        <n-data-table
          :columns="columns"
          :data="userAccounts"
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
import { ref, onMounted, reactive, h } from 'vue';
import type { Ref } from 'vue';
import { NTag, NSpace, NButton } from 'naive-ui';
import type { DataTableColumns, PaginationProps } from 'naive-ui';
// eslint-disable-next-line import/order
import { useLoading } from '@/hooks';

// === 核心修改点：这里路径错了，应该是 @/api/auth ===
import { fetchAllUserAccounts } from '@/types/auth'; // <--- **已修正为 @/api/auth**
import type { UserAccount } from '@/types/user-list';
import type { UserRole } from '@/types/user-common';

const { loading, startLoading, endLoading } = useLoading(false);
const userAccounts = ref<UserAccount[]>([]);
const errorMsg = ref<string | null>(null);

// 角色标签的颜色映射 (确保包含 'admin' 角色)
const roleTagMap: Record<UserRole, NaiveUI.ThemeColor> = {
  admin: 'error',
  teacher: 'info',
  student: 'success'
};

// 分页配置 (保持不变)
const pagination: PaginationProps = reactive({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 15, 20, 25, 30],
  itemCount: 0,
  onChange: (page: number) => {
    pagination.page = page;
    // 如果后端支持分页，这里需要重新调用 fetchUserAccounts 并传入分页参数
    // fetchUserAccounts();
  },
  onUpdatePageSize: (pageSize: number) => {
    pagination.pageSize = pageSize;
    pagination.page = 1;
    // 如果后端支持分页，这里需要重新调用 fetchUserAccounts 并传入分页参数
    // fetchUserAccounts();
  }
});

/**
 * 获取用户账户列表
 */
async function fetchUserAccounts() {
  startLoading();
  errorMsg.value = null;

  try {
    // 调用 auth.ts 中的函数来获取数据
    const data = await fetchAllUserAccounts(); // 使用封装好的 API 函数

    // 调试日志：检查从 API 获取的原始数据
    // eslint-disable-next-line no-console
    console.log('数据 from API:', data);

    if (data && Array.isArray(data) && data.length > 0) {
      // 确保data是数组且不为空
      userAccounts.value = data.map((item, index) => ({
        ...item,
        index: index + 1 // 在前端为数据添加序号
      }));
      pagination.itemCount = data.length;

      // 调试日志：检查赋值到 userAccounts.value 后的数据
      // eslint-disable-next-line no-console
      console.log('userAccounts.value (after assignment):', userAccounts.value);
    } else {
      userAccounts.value = [];
      pagination.itemCount = 0;
      // eslint-disable-next-line no-console
      console.log('没有用户账户数据或数据为空。');
    }
    window.$message?.success('账户列表加载成功！');
  } catch (error: any) {
    // eslint-disable-next-line no-console
    console.error('Failed to fetch user accounts:', error);
    if (error.response && error.response.data && error.response.data.message) {
      errorMsg.value = `无法加载用户账户：${error.response.data.message}`;
    } else {
      errorMsg.value = '无法加载用户账户。请检查网络或稍后再试。';
    }
    window.$message?.error('账户列表加载失败！');
    userAccounts.value = [];
    pagination.itemCount = 0;
  } finally {
    endLoading();
  }
}

// 定义表格列 (保持不变)
const columns: Ref<DataTableColumns<UserAccount>> = ref([
  {
    key: 'index',
    title: '序号',
    align: 'center',
    width: 60,
    render: (_row, index) => {
      return index + 1;
    }
  },
  {
    key: 'id',
    title: '用户ID',
    align: 'center',
    width: 80
  },
  {
    key: 'username',
    title: '用户名',
    align: 'left',
    minWidth: 150
  },
  {
    key: 'role',
    title: '角色',
    align: 'center',
    width: 100,
    render: row => {
      return h(
        NTag,
        { type: roleTagMap[row.role] || 'default', bordered: false },
        {
          default: () => {
            switch (row.role) {
              case 'admin':
                return '管理员';
              case 'teacher':
                return '教师';
              case 'student':
                return '学生';
              default:
                return row.role;
            }
          }
        }
      );
    }
  },
  {
    key: 'created_at',
    title: '创建时间',
    align: 'center',
    width: 180,
    render: row => {
      const date = new Date(row.created_at);
      return date.toLocaleString();
    }
  },
  {
    key: 'updated_at',
    title: '更新时间',
    align: 'center',
    width: 180,
    render: row => {
      const date = new Date(row.updated_at);
      return date.toLocaleString();
    }
  },
  {
    key: 'actions',
    title: '操作',
    align: 'center',
    width: 120,
    render: row => {
      return h(NSpace, { justify: 'center' }, [
        h(NButton, { size: 'small', onClick: () => handleViewDetails(row) }, { default: () => '查看' })
      ]);
    }
  }
]) as Ref<DataTableColumns<UserAccount>>;

function rowKey(rowData: UserAccount) {
  return rowData.id;
}

function handleViewDetails(row: UserAccount) {
  window.$message?.info(`查看用户详情：${row.username} (ID: ${row.id})`);
  // eslint-disable-next-line no-console
  console.log('User details:', row);
}

onMounted(() => {
  fetchUserAccounts();
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
  min-height: 0;
}
</style>
