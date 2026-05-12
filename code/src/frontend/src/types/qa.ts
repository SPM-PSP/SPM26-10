// src/types/qa.ts

/**
 * 在线问答请求的数据结构
 */
export interface OnlineQARequestPayload {
  question: string;
  // 如果需要学生ID或其他标识，可以在这里添加
  // student_id?: string;
}

/**
 * 在线问答API的响应数据结构
 */
export interface OnlineQAApiResponse {
  status: 'success' | 'error';
  question: string;
  answer: string; // 智能回答内容，纯文本
  // 如果有其他返回字段，例如 generated_at, resource_id 等，可以在这里添加
  generated_at?: string;
  resource_id?: string;
}
