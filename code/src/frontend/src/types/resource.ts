// src/types/resource.ts

// 定义资源类型
export type ResourceType = 'assessment' | 'practice' | 'lesson_plan';

// 定义 metadata_json 中可能的字段及其类型
// 使用 Record<string, any> 是一个灵活的选项，但如果已知具体字段，最好明确定义
export interface ResourceMetadata {
  num_questions?: number; // ? 表示可选
  question_type?: string;
  difficulty_level?: string;
  programming_language?: string | null; // null 是可能的，所以要加上
  student_id?: string;
  topic_focus?: string | null; // null 是可能的
  course_level?: string;
  expected_duration_hours?: number | null; // null 是可能的
  // ... 其他可能的元数据字段
  [key: string]: any; // 允许有其他未明确定义的字段
}

// 定义教师资源接口
export interface TeacherResource {
  id: string; // 注意：这里是 UUID，所以是 string 类型
  title: string;
  resource_type: ResourceType;
  created_by_user_id: number;
  created_at: string;
  file_path: string;
  metadata_json: ResourceMetadata; // 使用上面定义的元数据接口
  subject: string | null; // null 是可能的，所以要加上
}
