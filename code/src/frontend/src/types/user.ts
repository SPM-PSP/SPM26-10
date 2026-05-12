// src/types/user.ts

// 定义用户角色的联合类型，假设后端只接受这些值
export type UserRole = 'teacher' | 'student'; // <--- 确保这一行存在且有 'export' 关键字

export interface CreateUserAccountPayload {
  username: string;
  password: string;
  role: UserRole;
}

export interface CreateUserAccountResponse {
  // <--- 确保这一接口存在且有 'export' 关键字
  status: string;
  message: string;
  user_id: number;
}
export interface UserAccount {
  id: number;
  username: string;
  role: UserRole;
  created_at: string; // 示例日期字符串，可以转换为 Date 对象
  updated_at: string; // 示例日期字符串，可以转换为 Date 对象
}
