<template>
  <div class="h-full overflow-hidden">
    <n-space vertical :size="20">
      <n-card title="创建用户" :bordered="false" class="rounded-8px shadow-sm">
        <n-form ref="formRef" :model="formModel" :rules="rules" label-placement="left" :style="{ maxWidth: '520px' }">
          <n-form-item label="用户名" path="username">
            <n-input v-model:value="formModel.username" placeholder="请输入用户名" />
          </n-form-item>
          <n-form-item label="密码" path="password">
            <n-input v-model:value="formModel.password" type="password" show-password-on="click" placeholder="请输入密码" />
          </n-form-item>
          <n-form-item label="角色" path="role">
            <n-select v-model:value="formModel.role" :options="roleOptions" placeholder="请选择角色" />
          </n-form-item>
          <n-space>
            <n-button type="primary" :loading="creating" @click="handleCreateUser">创建用户</n-button>
            <n-button @click="resetForm">重置</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-card title="用户列表" :bordered="false" class="rounded-8px shadow-sm">
        <n-space justify="end" class="mb-12px">
          <n-button type="primary" secondary :loading="loading" @click="fetchUsers">刷新列表</n-button>
        </n-space>
        <loading-empty-wrapper class="h-480px" :loading="loading" :empty="users.length === 0">
          <n-data-table :columns="columns" :data="users" :row-key="row => row.id" class="h-480px" flex-height />
        </loading-empty-wrapper>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { NTag } from 'naive-ui';
import type { DataTableColumns, FormInst, FormRules } from 'naive-ui';
import _axios from '@/utils/request';

defineOptions({ name: 'AdminUserManagementPage' });

type UserRole = 'admin' | 'teacher' | 'student';

interface UserItem {
  id: number;
  username: string;
  role: UserRole;
  created_at: string;
  updated_at: string;
}

interface CreateUserResponse {
  status: string;
  message: string;
  user_id?: number;
}

const formRef = ref<FormInst | null>(null);
const creating = ref(false);
const loading = ref(false);
const users = ref<UserItem[]>([]);

const formModel = reactive({
  username: '',
  password: '',
  role: 'teacher' as UserRole
});

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '教师', value: 'teacher' },
  { label: '学生', value: 'student' }
];

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应为 3-20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为 6 位', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
};

const roleTagType = computed<Record<UserRole, 'error' | 'info' | 'success'>>(() => ({
  admin: 'error',
  teacher: 'info',
  student: 'success'
}));

const columns: DataTableColumns<UserItem> = [
  { title: 'ID', key: 'id', width: 80, align: 'center' },
  { title: '用户名', key: 'username', minWidth: 140 },
  {
    title: '角色',
    key: 'role',
    width: 120,
    render: row =>
      h(
        NTag,
        { bordered: false, type: roleTagType.value[row.role] },
        { default: () => ({ admin: '管理员', teacher: '教师', student: '学生' })[row.role] }
      )
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render: row => new Date(row.created_at).toLocaleString()
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 180,
    render: row => new Date(row.updated_at).toLocaleString()
  }
];

async function fetchUsers() {
  loading.value = true;
  try {
    const response = await _axios.get<UserItem[]>('/api/admin/users');
    users.value = Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('获取用户列表失败:', error);
    users.value = [];
  } finally {
    loading.value = false;
  }
}

async function handleCreateUser() {
  try {
    await formRef.value?.validate();
    creating.value = true;

    const response = await _axios.post<CreateUserResponse>('/api/admin/users/create', formModel);
    if (response.data.status !== 'success') {
      throw new Error(response.data.message || '创建用户失败');
    }

    window.$message?.success(response.data.message || '创建用户成功');
    resetForm();
    await fetchUsers();
  } catch (error: any) {
    console.error('创建用户失败:', error);
    window.$message?.error(error?.response?.data?.detail || error?.message || '创建用户失败');
  } finally {
    creating.value = false;
  }
}

function resetForm() {
  formModel.username = '';
  formModel.password = '';
  formModel.role = 'teacher';
  formRef.value?.restoreValidation();
}

onMounted(() => {
  fetchUsers();
});
</script>
