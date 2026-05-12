// src/types/answer.ts

/**
 * 答案批改请求的数据结构
 */
export interface AnswerCorrectRequestPayload {
  question: string;
  student_answer: string;
  reference_answer: string;
  student_id: string; // 根据您的需求，这里可以是 number 或 string
}

/**
 * 答案批改API的响应数据结构
 */
export interface AnswerCorrectApiResponse {
  status: 'success' | 'error';
  feedback: string; // 批改反馈内容，Markdown 格式
  corrected_at: string;
}
