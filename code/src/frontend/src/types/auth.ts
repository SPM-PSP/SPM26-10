// src/api/auth.ts

// 导入您的 axios 实例，用于发起 HTTP 请求
import _axios from '@/utils/request';
// 导入 user-list.ts 中定义的用户账户类型
import type { UserAccount } from '@/types/user-list';

/**
 * 从后端获取所有用户账户列表。
 * @returns Promise<UserAccount[]> 返回一个包含用户账户数组的 Promise。
 */
export async function fetchAllUserAccounts(): Promise<UserAccount[]> {
  const response = await _axios.get<UserAccount[]>('/api/admin/users');
  // Axios 的响应数据通常在 response.data 属性中
  return response.data;
}

// 如果将来有其他认证相关的 API（如登录、注册），也可以在此文件中添加：
// import type { LoginPayload, LoginResponse } from '@/types/some-auth-payload-types';
// export async function login(payload: LoginPayload): Promise<LoginResponse> {
//   const response = await _axios.post<LoginResponse>('/api/login', payload);
//   return response.data;
// }
