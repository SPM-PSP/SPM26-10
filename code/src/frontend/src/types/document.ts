// src/types/document.ts
/**
 * 课程大纲的基本信息
 */
export interface CourseOutlineInfo {
  /** 课程大纲的标题或主题 */
  course_outline: string;
  /** 课程的难度级别或适用年级 */
  course_level: string;
  /** 预期的课程持续时间（小时），可以为 null */
  expected_duration_hours: number | null; // <-- 再次确认，必须是 number | null
}

/**
 * 课程计划的详细时间分布项
 */
export interface LessonPlanTimeDistributionItem {
  /** 部分名称 */
  部分: string;
  /** 时间 */
  时间: string;
  /** 具体内容 */
  具体内容: string;
}

/**
 * 完整的课程计划内容
 */
export interface LessonPlanContent {
  /** 课程计划的Markdown格式文本 */
  lesson_plan: string;
  /** 计划生成的时间，ISO 8601格式 */
  generated_at: string;
}

/**
 * 包含课程计划的API响应结构
 */
export interface CoursePlanApiResponse {
  /** API请求的状态，通常为 "success" 或 "error" */
  status: 'success' | 'error';
  /** 课程计划的详细内容 */
  lesson_plan: string; // 这里的 lesson_plan 字段是直接包含 Markdown 格式的字符串
  /** 计划生成的时间，ISO 8601格式 */
  generated_at: string;
}
