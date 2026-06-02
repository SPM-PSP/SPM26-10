<template>
  <div class="h-full">
    <n-space vertical :size="20">
      <n-card title="加入班级" :bordered="false" class="rounded-8px shadow-sm">
        <div class="pb-12px text-16px">输入教师提供的班级码，加入对应班级并接收已发布试卷。</div>
        <n-form ref="formRef" :model="joinForm" :rules="rules" size="large" label-placement="left" inline>
          <n-form-item label="班级码" path="class_code">
            <n-input v-model:value="joinForm.class_code" placeholder="例如：A8K2QX" />
          </n-form-item>
          <n-button type="primary" :loading="joining" @click="handleJoin">加入班级</n-button>
        </n-form>
      </n-card>

      <n-card title="我的班级" :bordered="false" class="rounded-8px shadow-sm">
        <n-spin :show="loading">
          <template v-if="classes.length">
            <n-grid cols="1 s:2 l:3" responsive="screen" :x-gap="16" :y-gap="16">
              <n-grid-item v-for="item in classes" :key="item.id">
                <n-card :bordered="false" class="rounded-8px class-card" hoverable @click="goToPapers(item.id)">
                  <n-space vertical :size="10">
                    <div class="flex items-start justify-between gap-12px">
                      <div class="text-18px font-600">{{ item.name }}</div>
                      <n-tag :bordered="false" type="success">已加入</n-tag>
                    </div>
                    <div class="text-13px text-#64748b">班级码：{{ item.class_code }}</div>
                    <div class="text-13px text-#64748b">教师：{{ item.teacher_name || '未命名教师' }}</div>
                    <div class="text-13px text-#64748b">成员数：{{ item.member_count }}</div>
                    <div class="text-14px line-clamp-3 text-#475569">{{ item.description || '暂无班级说明。' }}</div>
                    <n-space :size="10">
                      <n-button size="small" @click.stop="goToPapers(item.id)">查看试卷</n-button>
                      <n-popconfirm @positive-click="leaveClass(item.id)">
                        <template #trigger>
                          <n-button size="small" type="warning" ghost @click.stop>退出班级</n-button>
                        </template>
                        退出后将无法继续查看该班级已发布试卷，确认退出？
                      </n-popconfirm>
                    </n-space>
                  </n-space>
                </n-card>
              </n-grid-item>
            </n-grid>
          </template>
          <template v-else>
            <n-empty description="你还没有加入任何班级。" />
          </template>
        </n-spin>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import type { FormInst, FormRules } from 'naive-ui';
import { useRouter } from 'vue-router';
import { createRequiredFormRule } from '@/utils/form/rule';
import _axios from '@/utils/request';

defineOptions({ name: 'StudentClassesPage' });

interface ClassItem {
  id: string;
  name: string;
  description?: string | null;
  class_code: string;
  teacher_id: number;
  teacher_name?: string | null;
  created_at: string;
  updated_at: string;
  member_count: number;
  status: string;
}

const router = useRouter();
const formRef = ref<FormInst | null>(null);
const loading = ref(false);
const joining = ref(false);
const classes = ref<ClassItem[]>([]);

const joinForm = reactive({
  class_code: ''
});

const rules: FormRules = {
  class_code: [createRequiredFormRule('请输入班级码')]
};

async function fetchClasses() {
  loading.value = true;
  try {
    const response = await _axios.get<ClassItem[]>('/api/student/classes');
    classes.value = response.data;
  } catch (error: any) {
    console.error('获取班级列表失败:', error);
    window.$message?.error(error?.response?.data?.detail || '获取班级列表失败');
  } finally {
    loading.value = false;
  }
}

async function handleJoin() {
  try {
    await formRef.value?.validate();
    joining.value = true;
    await _axios.post('/api/student/classes/join', { class_code: joinForm.class_code.trim().toUpperCase() });
    window.$message?.success('加入班级成功');
    joinForm.class_code = '';
    await fetchClasses();
  } catch (error: any) {
    if (error?.response) {
      window.$message?.error(error.response.data?.detail || '加入班级失败');
    }
  } finally {
    joining.value = false;
  }
}

async function leaveClass(classId: string) {
  try {
    await _axios.post(`/api/student/classes/${classId}/leave`);
    window.$message?.success('已退出班级');
    await fetchClasses();
  } catch (error: any) {
    console.error('退出班级失败:', error);
    window.$message?.error(error?.response?.data?.detail || '退出班级失败');
  }
}

function goToPapers(classId: string) {
  router.push({ name: 'student_papers', query: { classId } });
}

onMounted(fetchClasses);
</script>

<style scoped>
.class-card {
  min-height: 220px;
}
</style>
