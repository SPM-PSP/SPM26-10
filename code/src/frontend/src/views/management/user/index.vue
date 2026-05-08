<template>
  <div class="overflow-hidden h-full">
    <n-card title="创建用户账户" :bordered="false" class="h-full rounded-8px shadow-sm">
      <n-form
        ref="formRef"
        :model="formModel"
        :rules="formRules"
        label-placement="left"
        label-width="auto"
        require-mark-placement="right-hanging"
        :style="{ maxWidth: '500px' }"
      >
        <n-form-item label="用户名" path="username">
          <n-input v-model:value="formModel.username" placeholder="请输入用户名" />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="formModel.password"
            type="password"
            show-password-on="click"
            placeholder="请输入密码"
          />
        </n-form-item>
        <n-form-item label="角色" path="role">
          <n-select v-model:value="formModel.role" :options="roleOptions" placeholder="请选择角色" />
        </n-form-item>
        <n-form-item>
          <n-space>
            <n-button type="primary" :loading="loading" @click="handleSubmit">创建账户</n-button>
            <n-button @click="handleReset">重置</n-button>
          </n-space>
        </n-form-item>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import type { FormInst, FormRules, SelectOption } from 'naive-ui';
import { useLoading } from '@/hooks';
import _axios from '@/utils/request'; // 引入您的 axios 实例
import type { CreateUserAccountPayload, CreateUserAccountResponse, UserRole } from '@/types/user'; // 引入更新后的类型定义

const { loading, startLoading, endLoading } = useLoading(false);

const formRef = ref<FormInst | null>(null);

// 表单模型，初始化默认值
const formModel = reactive<CreateUserAccountPayload>({
  username: '',
  password: '',
  role: 'teacher' // 默认选中 'teacher'
});

// 角色选项
const roleOptions: SelectOption[] = [
  { label: '教师', value: 'teacher' as UserRole },
  { label: '学生', value: 'student' as UserRole }
];

// 表单验证规则
const formRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应为3-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少为6位', trigger: 'blur' }
  ],
  role: [
    // 角色现在是必选的
    { required: true, message: '请选择角色', trigger: 'change', type: 'enum', enum: ['teacher', 'student', 'admin'] }
  ]
};

/**
 * 提交表单创建用户账户
 */
async function handleSubmit() {
  formRef.value?.validate(async errors => {
    if (!errors) {
      startLoading();
      try {
        // payload 直接使用 formModel，因为它包含了 role 字段
        const payload: CreateUserAccountPayload = {
          username: formModel.username,
          password: formModel.password,
          role: formModel.role // <--- role 字段现在会发送给后端
        };

        const response = await _axios.post<CreateUserAccountResponse>('/api/admin/users/create', payload);

        if (response.data.status === 'success') {
          window.$message?.success(response.data.message || '用户账户创建成功！');
          handleReset(); // 创建成功后清空表单
        } else {
          // 即使状态不是 success，也可能是 200 OK，但后端逻辑失败
          window.$message?.error(response.data.message || '创建用户账户失败！');
        }
      } catch (error) {
        // 错误已经在 _axios 拦截器中处理，这里可以做一些额外处理
        console.error('Error creating user account:', error);
      } finally {
        endLoading();
      }
    } else {
      window.$message?.error('请检查表单填写！');
    }
  });
}

/**
 * 重置表单
 */
function handleReset() {
  formModel.username = '';
  formModel.password = '';
  formModel.role = 'teacher'; // 重置角色选择为默认值 'teacher'
  formRef.value?.restoreValidation(); // 清除验证状态
}
</script>

<style scoped>
.h-full {
  height: 100%;
}
.overflow-hidden {
  overflow: hidden;
}
</style>
