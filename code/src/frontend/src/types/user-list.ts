// src/types/user-list.ts

// 导入 UserRole 类型，因为它在 UserAccount 接口中被使用
import type { UserRole } from './user-common';

// 用于获取用户列表的接口定义
export interface UserAccount {
  id: number;
  username: string;
  role: UserRole; // 使用导入的 UserRole 类型
  created_at: string;
  updated_at: string;
}
