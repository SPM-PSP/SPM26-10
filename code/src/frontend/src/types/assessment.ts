// src/types/assessment.ts

/**
 * 考核题目生成请求的数据结构
 */
export interface AssessmentRequestPayload {
  topic: string;
  question_type: string | null;
  difficulty_level: string | null;
  num_questions: number | null;
}

/**
 * 考核题目生成API的响应数据结构
 */
export interface AssessmentApiResponse {
  status: 'success' | 'error';
  assessment_content: string; // 考核题目内容，Markdown 格式
  generated_at: string;
  resource_id: string;
}
