// src/utils/request.ts
import { createDiscreteApi } from 'naive-ui';
import axios from 'axios';
// import router from '@/router'; // 如果在拦截器中直接用到 router，需要确保其在项目中的可访问性

const { message } = createDiscreteApi(['message']);

const BASE_URL = import.meta.env.VITE_APP_BASE_URL || 'http://localhost:8000'; // 提供一个回退的默认值
// eslint-disable-next-line no-underscore-dangle
const _axios = axios.create({
  baseURL: BASE_URL, // **请根据您的实际后端地址修改**
  timeout: 1000000,
  headers: {
    'Content-Type': 'application/json'
  }
});

_axios.interceptors.request.use(
  config => {
    // === 关键修改：避免 OPTIONS 预检请求携带数据或被不当修改 ===
    // 如果请求方法是 OPTIONS，直接返回原始配置，不做任何修改
    // OPTIONS 请求不应包含请求体，也不应有复杂的自定义头部，除非后端明确要求
    if (config.method && config.method.toLowerCase() === 'options') {
      return config;
    }
    // === 结束关键修改 ===

    const sessionId = sessionStorage.getItem('session_id');
    if (sessionId) {
      config.headers['X-Session-ID'] = sessionId; // 或其他您后端需要的头部
    }
    // 如果您有其他通用的请求头或数据处理逻辑，请放在这里
    // 确保这些逻辑不会在 OPTIONS 请求时被触发

    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

_axios.interceptors.response.use(
  response => {
    return response;
  },
  error => {
    // eslint-disable-next-line no-console
    console.error('API 请求出错:', error);
    let errorMessage = '网络错误或服务器无响应，请稍后再试。';

    if (error.response) {
      const { status, data } = error.response;
      if (data && data.message) {
        errorMessage = data.message;
      } else {
        switch (status) {
          case 400:
            errorMessage = '请求参数错误 (400)';
            break;
          case 401:
            errorMessage = '认证失败，请重新登录 (401)';
            sessionStorage.removeItem('session_id');
            // 如果需要在拦截器中跳转路由，确保此处可以访问 router 实例
            // 例如：如果 router 是一个全局单例，或者通过 provide/inject
            // 或者更常见的，在业务逻辑中捕获 401 错误后跳转
            break;
          case 403:
            errorMessage = '无权限访问 (403)';
            break;
          case 404:
            errorMessage = '请求的资源不存在 (404)';
            break;
          case 500:
            errorMessage = '服务器内部错误 (500)';
            break;
          default:
            errorMessage = `请求失败: ${status}`;
        }
      }
    } else if (error.request) {
      errorMessage = '服务器无响应，请检查网络。';
    } else {
      errorMessage = '请求配置错误。';
    }

    message.error(errorMessage); // 使用 Naive UI 提示错误
    return Promise.reject(error);
  }
);

// ======== CRITICAL: This line makes it a module ========
export default _axios;
