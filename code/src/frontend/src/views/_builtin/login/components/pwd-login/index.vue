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
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useMessage, type FormInst, type FormRules, type FormItemRule } from 'naive-ui';
import { useAuthStore } from '@/store';

const loginModuleLabels = {
  'code-login': '验证码登录',
  register: '注册'
};

const message = useMessage();
const auth = useAuthStore();
const router = useRouter();

const formRef = ref<FormInst | null>(null);

const model = reactive({
  userName: 'admin',
  password: '123456'
});

const loginLoading = ref(false);
const rememberMe = ref(false);

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
  ] as FormItemRule[]
};

async function handleSubmit() {
  try {
    await formRef.value?.validate();
    loginLoading.value = true;
    await auth.login(model.userName, model.password);
    message.success('登录成功！');
  } catch (error: any) {
    console.error('登录请求或表单验证失败:', error);
    const detailMessage =
      error?.response?.data?.detail?.message || error?.response?.data?.message || error?.message || '登录失败，请重试。';
    message.error(detailMessage);
  } finally {
    loginLoading.value = false;
  }
}

function toLoginModule(moduleName: string) {
  switch (moduleName) {
    case 'reset-pwd':
      router.push('/login/reset-pwd');
      break;
    case 'code-login':
      router.push('/login/code-login');
      break;
    case 'register':
      router.push('/login/register');
      break;
    default:
      console.warn(`未知登录模块: ${moduleName}`);
  }
}
</script>

<style scoped></style>
