<!-- eslint-disable no-console -->
<template>
  <n-form ref="formRef" :model="model" :rules="rules" size="large" :show-label="false">
    <n-form-item path="userName">
      <n-input v-model:value="model.userName" :placeholder="$t('page.login.common.userNamePlaceholder')" />
    </n-form-item>
    <n-form-item path="password">
      <n-input
        v-model:value="model.password"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.common.passwordPlaceholder')"
      />
    </n-form-item>

    <n-form-item path="selectedRole">
      <n-select v-model:value="model.selectedRole" :options="roleOptions" placeholder="请选择登录角色" />
    </n-form-item>

    <n-space :vertical="true" :size="18">
      <div class="flex-y-center justify-between">
        <n-checkbox v-model:checked="rememberMe">
          {{ $t('page.login.pwdLogin.rememberMe') }}
        </n-checkbox>
        <n-button :text="true" @click="toLoginModule('reset-pwd')">
          {{ $t('page.login.pwdLogin.forgetPassword') }}
        </n-button>
      </div>
      <n-button
        type="primary"
        size="large"
        :block="true"
        :round="true"
        :loading="loginLoading"
        @click="handleSubmit"
      >
        {{ $t('page.login.common.confirm') }}
      </n-button>
      <div class="flex-y-center justify-between">
        <n-button class="flex-1" :block="true" @click="toLoginModule('code-login')">
          {{ loginModuleLabels['code-login'] }}
        </n-button>
        <div class="w-12px"></div>
        <n-button class="flex-1" :block="true" @click="toLoginModule('register')">
          {{ loginModuleLabels.register }}
        </n-button>
      </div>
    </n-space>
  </n-form>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'; // 引入 computed
import { useRouter } from 'vue-router';
import { useMessage, type FormInst, type FormRules, type FormItemRule } from 'naive-ui';
import _axios from '@/utils/request';

// ========= 本地常量定义 =========
const loginModuleLabels = {
  'code-login': '验证码登录',
  register: '注册'
};

// ========= Naive UI 相关 Hook =========
const message = useMessage();
// ========= Vue Router 相关 Hook =========
const router = useRouter();

// ========= 响应式数据和引用 =========
const formRef = ref<FormInst | null>(null);

const model = reactive({
  userName: 'admin',
  password: '123456',
  // === 新增：用户选择的角色，初始值设置为默认角色 ===
  selectedRole: 'user' // 默认值，确保是 Auth.RoleType 中的一个
});

const loginLoading = ref(false);
const rememberMe = ref(false);

// ========= 角色选项定义 =========
// 这里的 value 必须和你的 Auth.RoleType (super, admin, user) 保持一致
const roleOptions = computed(() => [
  { label: '学生', value: 'user' },
  { label: '管理员 ', value: 'admin' },
  { label: '老师', value: 'super' }
]);

// ========= 表单验证规则 =========
const rules: FormRules = {
  userName: {
    required: true,
    message: '请输入用户名',
    trigger: ['blur', 'input']
  },
  password: [
    {
      required: true,
      message: '请输入密码',
      trigger: ['blur', 'input']
    },
    {
      min: 6,
      message: '密码长度不能少于6位',
      trigger: ['blur', 'input']
    }
  ] as FormItemRule[],
  // === 新增：角色选择的验证规则 (可选，但推荐) ===
  selectedRole: {
    required: true,
    message: '请选择登录角色',
    trigger: ['change']
  }
};

// ========= 核心登录处理函数 =========
async function handleSubmit() {
  try {
    // 1. 触发表单验证
    await formRef.value?.validate();

    // 2. 设置登录按钮为加载状态
    loginLoading.value = true;

    // 3. 提取用户名、密码和选择的角色
    const { userName, password, selectedRole } = model;

    // 4. 发送登录请求 (这里假设后端不返回角色，角色由前端选择决定)
    // 如果后端会返回角色，请根据后端返回的角色来设置，而不是前端选择的
    const response = await _axios.post('/api/login', {
      username: userName,
      password
      // 如果后端需要知道前端选择的角色，可以在这里添加 role 参数
      // role: selectedRole
    });

    // 5. 处理后端响应
    if (response.data.status === 'success') {
      const sessionId = response.data.session_id;

      // === 核心：将 session_id 和 用户选择的角色存储到 sessionStorage ===
      sessionStorage.setItem('session_id', sessionId);

      // 将用户选择的角色也存储到 sessionStorage，供 permission.ts 读取
      // 这里将用户选择的角色作为 userRole 存储在 userInfo 对象中
      const userInfo = {
        userId: 'some_id_from_backend', // 如果后端有返回，请用实际的id
        userName,
        userRole: selectedRole // 存储用户选择的角色
      };
      sessionStorage.setItem('user_info', JSON.stringify(userInfo)); // 将整个 userInfo 对象字符串化存储

      // 弹出成功消息
      message.success(response.data.message || '登录成功！');
      // eslint-disable-next-line no-console
      console.log('尝试跳转到 /dashboard');
      // 6. 导航到仪表盘页面
      router.push('/dashboard');
      // eslint-disable-next-line no-console
      console.log('already /dashboard');
    } else {
      // 后端返回 status 不是 'success'，说明登录失败
      const errorMessage = response.data.message || '登录失败，请检查用户名、密码。';
      message.error(errorMessage);
    }
  } catch (error: any) {
    console.error('登录请求或表单验证失败:', error);
    if (!error.response && !error.request) {
      console.warn('表单验证未通过，请根据提示修正输入。');
    }
  } finally {
    // 7. 无论登录成功或失败，都解除加载状态
    loginLoading.value = false;
  }
}

// ========= 模块跳转逻辑 =========
function toLoginModule(moduleName: string) {
  switch (moduleName) {
    case 'reset-pwd':
      router.push('/password_reset');
      break;
    case 'code-login':
      router.push('/login/code');
      break;
    case 'register':
      router.push('/register');
      break;
    default:
      console.warn(`未知登录模块: ${moduleName}`);
  }
}
</script>

<style scoped></style>
