<template>
  <div class="h-full overflow-hidden">
    <n-card title="表格" :bordered="false" class="h-full rounded-8px shadow-sm">
      <n-space :vertical="true">
        <n-space>
          <n-button @click="getDataSource">有数据</n-button>
          <n-button @click="getEmptyDataSource">空数据</n-button>
        </n-space>
        <loading-empty-wrapper class="h-480px" :loading="loading" :empty="empty">
          <n-data-table :columns="columns" :data="dataSource" :flex-height="true" class="h-480px" />
        </loading-empty-wrapper>
      </n-space>
    </n-card>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue';
import type { DataTableColumns } from 'naive-ui';
import { useLoadingEmpty } from '@/composables';

interface UserData {
  id: number;
  username: string;
  role: string;
  created_at: string | null;
  updated_at: string | null;
}

const { loading, startLoading, endLoading, empty, setEmpty } = useLoadingEmpty();

const dataSource = ref<UserData[]>([]);

const columns: DataTableColumns<UserData> = [
  {
    title: 'ID',
    key: 'id',
    width: 80,
    align: 'center'
  },
  {
    title: '用户名',
    key: 'username',
    minWidth: 120
  },
  {
    title: '角色',
    key: 'role',
    render: row => {
      const roleMap: Record<string, string> = {
        admin: '管理员',
        teacher: '教师',
        student: '学生'
      };
      return roleMap[row.role] || row.role;
    }
  },
  {
    title: '创建时间',
    key: 'created_at',
    render: row => row.created_at || '-'
  },
  {
    title: '更新时间',
    key: 'updated_at',
    render: row => row.updated_at || '-'
  }
];

async function fetchData() {
  startLoading();
  try {
    const response = await fetch('<YOUR_SERVER_BASE_URL>/admin/users', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': localStorage.getItem('session_id') || '' // 从本地存储获取session
      }
    });

    if (!response.ok) {
      throw new Error(`请求失败: ${response.status}`);
    }

    const data: UserData[] = await response.json();
    dataSource.value = data;
    setEmpty(data.length === 0);
  } catch (error) {
    console.error('获取用户数据失败:', error);
    window.$message?.error('获取数据失败，请重试');
    dataSource.value = [];
    setEmpty(true);
  } finally {
    endLoading();
  }
}

function getDataSource() {
  fetchData();
}

function getEmptyDataSource() {
  startLoading();
  setTimeout(() => {
    dataSource.value = [];
    setEmpty(true);
    endLoading();
  }, 500);
}
</script>

<template>
  <div class="h-full overflow-hidden">
    <n-card title="用户管理" :bordered="false" class="h-full rounded-8px shadow-sm">
      <n-space :vertical="true">
        <n-space>
          <n-button @click="getDataSource" type="primary">获取用户数据</n-button>
          <n-button @click="getEmptyDataSource">显示空数据</n-button>
        </n-space>
        <loading-empty-wrapper class="h-480px" :loading="loading" :empty="empty">
          <n-data-table
            :columns="columns"
            :data="dataSource"
            :flex-height="true"
            class="h-480px"
            :row-key="row => row.id"
            scroll-x="1200"
          />
        </loading-empty-wrapper>
      </n-space>
    </n-card>
  </div>
</template>
