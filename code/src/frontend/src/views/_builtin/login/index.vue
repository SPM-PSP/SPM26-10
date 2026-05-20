<template>
  <div class="relative flex-center wh-full" :style="{ backgroundColor: bgColor }">
    <dark-mode-switch
      :dark="theme.darkMode"
      class="absolute left-48px top-24px z-3 text-20px"
      @update:dark="theme.setDarkMode"
    />
    <n-card
      :bordered="false"
      size="large"
      :class="['z-4 !w-auto rounded-20px login-shell-card', theme.darkMode ? 'login-shell-card--dark' : 'login-shell-card--light']"
    >
      <div class="w-300px sm:w-360px">
        <header class="flex items-center gap-20px">
          <system-logo class="text-64px text-primary" />
          <div class="flex flex-col">
            <n-gradient-text type="primary" :size="36">{{ $t('system.title') }}</n-gradient-text>
            <div class="subtitle text-16px text-[#666] dark:text-[#aaa] mt--0.5">
              {{ $t('system.subtitle') }}
            </div>
          </div>
        </header>
        <main class="pt-24px">
          <h3 class="text-18px text-primary font-medium">{{ activeModule.label }}</h3>
          <div class="pt-24px">
            <transition name="fade-slide" mode="out-in" appear>
              <component :is="activeModule.component" />
            </transition>
          </div>
        </main>
      </div>
    </n-card>
    <login-bg :theme-color="bgThemeColor" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Component } from 'vue';
import { loginModuleLabels } from '@/constants';
import { useThemeStore } from '@/store';
import { getColorPalette, mixColor } from '@/utils';
import { $t } from '@/locales';
import { BindWechat, CodeLogin, LoginBg, PwdLogin, Register, ResetPwd } from './components';

interface Props {
  /** 登录模块分类 */
  module: UnionKey.LoginModule;
}

const props = defineProps<Props>();

const theme = useThemeStore();

interface LoginModule {
  key: UnionKey.LoginModule;
  label: string;
  component: Component;
}

const modules: LoginModule[] = [
  { key: 'pwd-login', label: loginModuleLabels['pwd-login'], component: PwdLogin },
  { key: 'code-login', label: loginModuleLabels['code-login'], component: CodeLogin },
  { key: 'register', label: loginModuleLabels.register, component: Register },
  { key: 'reset-pwd', label: loginModuleLabels['reset-pwd'], component: ResetPwd },
  { key: 'bind-wechat', label: loginModuleLabels['bind-wechat'], component: BindWechat }
];

const activeModule = computed(() => {
  const active: LoginModule = { ...modules[0] };
  const findItem = modules.find(item => item.key === props.module);
  if (findItem) {
    Object.assign(active, findItem);
  }
  return active;
});

const bgThemeColor = computed(() => (theme.darkMode ? getColorPalette(theme.themeColor, 7) : theme.themeColor));

const bgColor = computed(() => {
  const COLOR_WHITE = '#ffffff';
  const ratio = theme.darkMode ? 0.5 : 0.2;
  return mixColor(COLOR_WHITE, theme.themeColor, ratio);
});
</script>

<style scoped>
.login-shell-card {
  transition:
    background-color 0.25s ease,
    border-color 0.25s ease,
    box-shadow 0.25s ease;
}

.login-shell-card--light {
  background: rgb(255 255 255 / 72%);
  border: 1px solid rgb(255 255 255 / 78%);
  box-shadow:
    0 28px 70px rgb(15 23 42 / 16%),
    0 10px 28px rgb(15 23 42 / 10%);
  backdrop-filter: blur(12px);
}

.login-shell-card--dark {
  background: rgb(9 14 24 / 72%);
  border: 1px solid rgb(71 85 105 / 42%);
  box-shadow:
    0 32px 80px rgb(2 6 23 / 42%),
    0 12px 30px rgb(2 6 23 / 28%);
  backdrop-filter: blur(14px);
}
</style>
