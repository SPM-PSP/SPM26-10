import { unref, nextTick } from 'vue';
import { defineStore } from 'pinia';
import { router } from '@/router';
import { useRouterPush } from '@/composables';
import { localStg } from '@/utils';
import { $t } from '@/locales';
import _axios from '@/utils/request';
import { useTabStore } from '../tab';
import { useRouteStore } from '../route';
import { getToken, getUserInfo, clearAuthStorage } from './helpers';

interface AuthState {
  /** 用户信息 */
  userInfo: Auth.UserInfo;
  /** 用户token */
  token: string;
  /** 登录的加载状态 */
  loginLoading: boolean;
}

export const useAuthStore = defineStore('auth-store', {
  state: (): AuthState => ({
    userInfo: getUserInfo(),
    token: getToken(),
    loginLoading: false
  }),
  getters: {
    /** 是否登录 */
    isLogin() {
      return Boolean(sessionStorage.getItem('session_id'));
    }
  },
  actions: {
    /** 重置auth状态 */
    resetAuthStore() {
      const { toLogin } = useRouterPush(false);
      const { resetTabStore } = useTabStore();
      const { resetRouteStore } = useRouteStore();
      const route = unref(router.currentRoute);
      const currentPath = route.fullPath;

      clearAuthStorage();
      this.$reset();

      toLogin(undefined, currentPath === '/login' ? undefined : currentPath);

      nextTick(() => {
        resetTabStore();
        resetRouteStore();
      });
    },
    setAuthSession(sessionId: string, userInfo: Auth.UserInfo) {
      sessionStorage.setItem('session_id', sessionId);
      sessionStorage.setItem('user_info', JSON.stringify(userInfo));
      localStg.set('token', sessionId);
      localStg.set('userInfo', userInfo);

      this.userInfo = userInfo;
      this.token = sessionId;
    },
    async fetchAndStoreUserInfo() {
      const response = await _axios.get('/api/getUserInfo');
      const userInfo: Auth.UserInfo = {
        userId: String(response.data.userId),
        userName: response.data.userName,
        userRole: response.data.userRole
      };
      localStg.set('userInfo', userInfo);
      sessionStorage.setItem('user_info', JSON.stringify(userInfo));
      this.userInfo = userInfo;
      this.token = getToken();
      return userInfo;
    },
    /**
     * 登录
     * @param userName - 用户名
     * @param password - 密码
     */
    async login(userName: string, password: string) {
      const route = useRouteStore();

      this.loginLoading = true;
      try {
        const response = await _axios.post('/api/login', {
          username: userName,
          password
        }, { skipGlobalErrorHandler: true } as any);

        if (response.data.status !== 'success' || !response.data.session_id) {
          throw new Error(response.data.message || '登录失败');
        }

        sessionStorage.setItem('session_id', response.data.session_id);
        localStg.set('token', response.data.session_id);

        const userInfo = await this.fetchAndStoreUserInfo();
        this.setAuthSession(response.data.session_id, userInfo);

        route.resetRouteStore();
        await route.initAuthRoute();
        await router.push({ name: route.routeHomeName });

        window.$notification?.success({
          title: $t('page.login.common.loginSuccess'),
          content: $t('page.login.common.welcomeBack', { userName: this.userInfo.userName }),
          duration: 3000
        });
      } catch (error) {
        clearAuthStorage();
        this.$reset();
        throw error;
      } finally {
        this.loginLoading = false;
      }
    }
  }
});
