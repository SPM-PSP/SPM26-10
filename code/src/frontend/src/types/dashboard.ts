// src/types/dashboard.ts

/**
 * 仪表盘指标API的响应数据结构
 */
export interface DashboardMetricsResponse {
  total_teachers: number;
  total_students: number;
  total_courses: number;
  avg_prep_time_hours: number;
  avg_correction_time_minutes: number;
  avg_student_accuracy: number;
  top_common_errors: string[];
  active_teachers_today: number;
  active_students_today: number;
  active_teachers_week: number;
  active_students_week: number;
  course_optimization_suggestions: string[];
}
