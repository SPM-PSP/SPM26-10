import type { Ref } from 'vue';
import type { FormItemRule } from 'naive-ui';
import { REGEXP_CODE_SIX, REGEXP_EMAIL, REGEXP_PHONE, REGEXP_PWD } from '@/config';

/** 创建自定义错误信息的必填表单规则 */
export const createRequiredFormRule = (message = '不能为空'): FormItemRule => ({ required: true, message });

export const requiredFormRule = createRequiredFormRule();

/** 表单规则 */
interface CustomFormRules {
  /** 手机号码 */
  phone: FormItemRule[];
  /** 密码 */
  pwd: FormItemRule[];
  /** 验证码 */
  code: FormItemRule[];
  /** 邮箱 */
  email: FormItemRule[];
  /** 课程大纲 */
  course_outline: FormItemRule[];
  /** 课程等级 */
  course_level: FormItemRule[];
  /** 预计课时 */
  expected_duration_hours: FormItemRule[];
  /** 考察内容 */
  topic: FormItemRule[];
  /** 题型 */
  question_type: FormItemRule[];
  /** 难度 */
  difficulty_level: FormItemRule[];
  /** 题目数量 */
  num_questions: FormItemRule[];
  /** 题目 */
  question: FormItemRule[];
  /** 学生答案 */
  student_answer: FormItemRule[];
  /** 参考答案 */
  reference_answer: FormItemRule[];
}

/** 表单规则 */
export const formRules: CustomFormRules = {
  phone: [
    createRequiredFormRule('请输入手机号码'),
    { pattern: REGEXP_PHONE, message: '手机号码格式错误', trigger: 'input' }
  ],
  pwd: [
    createRequiredFormRule('请输入密码'),
    { pattern: REGEXP_PWD, message: '密码为6-18位数字/字符/符号，至少2种组合', trigger: 'input' }
  ],
  code: [
    createRequiredFormRule('请输入验证码'),
    { pattern: REGEXP_CODE_SIX, message: '验证码格式错误', trigger: 'input' }
  ],
  email: [{ pattern: REGEXP_EMAIL, message: '邮箱格式错误', trigger: 'blur' }],
  course_outline: [createRequiredFormRule('请输入课程大纲')],
  course_level: [createRequiredFormRule('请输入课程等级')],
  expected_duration_hours: [
    createRequiredFormRule('请选择预计课时'),
    { validator: (_, value) => value >= 1 && value <= 99, message: '课时范围需在1-99之间', trigger: ['blur', 'change'] }
  ],
  topic: [createRequiredFormRule('请输入考察内容')],
  question_type: [createRequiredFormRule('请选择题型')],
  difficulty_level: [createRequiredFormRule('请选择难度')],
  num_questions: [
    createRequiredFormRule('请选择题目数量'),
    {
      validator: (_, value) => value >= 1 && value <= 99,
      message: '题目数量范围需在1-99之间',
      trigger: ['blur', 'change']
    }
  ],
  question: [createRequiredFormRule('请输入题目')],
  student_answer: [createRequiredFormRule('请输入学生答案')],
  reference_answer: [createRequiredFormRule('请输入参考答案')]
};

/** 是否为空字符串 */
function isBlankString(str: string) {
  return str.trim() === '';
}

/** 获取确认密码的表单规则 */
export function getConfirmPwdRule(pwd: Ref<string>) {
  const confirmPwdRule: FormItemRule[] = [
    { required: true, message: '请输入确认密码' },
    {
      validator: (rule, value) => {
        if (!isBlankString(value) && value !== pwd.value) {
          return Promise.reject(rule.message);
        }
        return Promise.resolve();
      },
      message: '输入的值与密码不一致',
      trigger: 'input'
    }
  ];
  return confirmPwdRule;
}

/** 获取图片验证码的表单规则 */
export function getImgCodeRule(imgCode: Ref<string>) {
  const imgCodeRule: FormItemRule[] = [
    { required: true, message: '请输入验证码' },
    {
      validator: (rule, value) => {
        if (!isBlankString(value) && value !== imgCode.value) {
          return Promise.reject(rule.message);
        }
        return Promise.resolve();
      },
      message: '验证码不正确',
      trigger: 'blur'
    }
  ];
  return imgCodeRule;
}
