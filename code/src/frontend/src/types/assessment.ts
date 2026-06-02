// src/types/assessment.ts

/**
 * 考核题目生成请求的数据结构
 */
export interface AssessmentRequestPayload {
  topic: string;
  question_type: string;
  difficulty_level: string;
  num_questions: number;
}

export interface GeneratedQuestion {
  id: string;
  resource_id: string;
  question_type: '选择题' | '填空题' | '简答题' | '编程题';
  question_content: string;
  options: string[];
  reference_answer?: string | null;
  score: number;
  difficulty_level?: string | null;
  sort_order: number;
  metadata_json?: Record<string, any> | null;
}

export interface GeneratedQuestionSet {
  id: string;
  title: string;
  resource_type: 'assessment' | 'practice';
  created_by_user_id: number;
  created_at: string;
  subject?: string | null;
  metadata_json?: Record<string, any> | null;
  content?: string | null;
  questions: GeneratedQuestion[];
}

/**
 * 考核题目生成API的响应数据结构
 */
export interface AssessmentApiResponse {
  status: 'success' | 'error';
  assessment_content: string; // 考核题目内容，Markdown 格式
  generated_at: string;
  resource_id: string;
  questions: GeneratedQuestion[];
}
