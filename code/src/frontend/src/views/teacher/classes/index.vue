<template>
  <div class="h-full">
    <n-space vertical :size="20">
      <n-card title="创建班级" :bordered="false" class="rounded-8px shadow-sm">
        <div class="pb-12px text-16px">创建班级后，系统会自动生成班级码，学生可凭班级码加入。</div>
        <n-form ref="formRef" :model="formModel" :rules="rules" size="large" label-placement="left">
          <n-grid cols="1 l:2" responsive="screen" :x-gap="16">
            <n-grid-item>
              <n-form-item label="班级名称" path="name">
                <n-input v-model:value="formModel.name" placeholder="例如：2026春嵌入式 Linux 1班" />
              </n-form-item>
            </n-grid-item>
            <n-grid-item>
              <n-form-item label="班级说明" path="description">
                <n-input
                  v-model:value="formModel.description"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 4 }"
                  placeholder="填写班级面向对象、课程安排或作业说明"
                />
              </n-form-item>
            </n-grid-item>
          </n-grid>
          <n-button type="primary" :loading="creating" @click="createClass">创建班级</n-button>
        </n-form>
      </n-card>

      <n-card title="我的班级" :bordered="false" class="rounded-8px shadow-sm">
        <n-spin :show="loading">
          <template v-if="classes.length">
            <n-grid cols="1 s:2 l:3" responsive="screen" :x-gap="16" :y-gap="16">
              <n-grid-item v-for="item in classes" :key="item.id">
                <n-card :bordered="false" class="rounded-8px class-card" hoverable @click="loadClassDetail(item.id)">
                  <n-space vertical :size="10">
                    <div class="flex items-start justify-between gap-12px">
                      <div class="text-18px font-600">{{ item.name }}</div>
                      <n-tag :type="item.status === 'dissolved' ? 'warning' : 'success'" :bordered="false">
                        {{ item.status === 'dissolved' ? '已解散' : '正常' }}
                      </n-tag>
                    </div>
                    <div class="text-13px text-#64748b">班级码：{{ item.class_code }}</div>
                    <div class="text-13px text-#64748b">成员数：{{ item.member_count }}</div>
                    <div class="text-14px text-#475569 line-clamp-3">{{ item.description || '暂无班级说明。' }}</div>
                    <n-space v-if="item.status !== 'dissolved'" :size="10">
                      <n-button size="small" @click.stop="loadClassDetail(item.id)">查看成员</n-button>
                      <n-popconfirm @positive-click="dissolveClass(item.id)">
                        <template #trigger>
                          <n-button size="small" type="warning" ghost @click.stop>解散班级</n-button>
                        </template>
                        解散后学生将无法继续加入或查看该班级试卷，确认继续？
                      </n-popconfirm>
                    </n-space>
                  </n-space>
                </n-card>
              </n-grid-item>
            </n-grid>
          </template>
          <template v-else>
            <n-empty description="还没有创建任何班级。" />
          </template>
        </n-spin>
      </n-card>

      <n-card title="班级成员" :bordered="false" class="rounded-8px shadow-sm">
        <template v-if="selectedClass">
          <n-space vertical :size="12">
            <div class="flex items-center justify-between gap-12px">
              <div>
                <div class="text-18px font-700">{{ selectedClass.name }}</div>
                <div class="text-14px text-#64748b">
                  班级码：{{ selectedClass.class_code }} ｜ 状态：{{ selectedClass.status === 'dissolved' ? '已解散' : '正常' }}
                </div>
              </div>
              <n-button @click="loadClassDetail(selectedClass.id)">刷新成员</n-button>
            </div>
            <n-data-table :columns="columns" :data="selectedClass.members" :pagination="{ pageSize: 8 }" />
          </n-space>
        </template>
        <template v-else>
          <n-empty description="点击上面的班级卡片后，这里会显示成员详情。" />
        </template>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import { NButton, NPopconfirm, NTag } from 'naive-ui';
import type { DataTableColumns, FormInst, FormRules } from 'naive-ui';
import { createRequiredFormRule } from '@/utils/form/rule';
import _axios from '@/utils/request';

defineOptions({ name: 'TeacherClassesPage' });

interface ClassMember {
  id: string;
  student_id: number;
  student_name: string;
  joined_at: string;
  status: string;
}

interface ClassItem {
  id: string;
  name: string;
  description?: string | null;
  class_code: string;
  member_count: number;
  status: string;
}

interface ClassDetail extends ClassItem {
  members: ClassMember[];
}

const formRef = ref<FormInst | null>(null);
const loading = ref(false);
const creating = ref(false);
const classes = ref<ClassItem[]>([]);
const selectedClass = ref<ClassDetail | null>(null);

const formModel = reactive({
  name: '',
  description: ''
});

const rules: FormRules = {
  name: [createRequiredFormRule('请输入班级名称')]
};

const columns: DataTableColumns<ClassMember> = [
  { title: '学生ID', key: 'student_id' },
  { title: '学生姓名', key: 'student_name' },
  {
    title: '加入时间',
    key: 'joined_at',
    render: row => h('span', new Date(row.joined_at).toLocaleString('zh-CN'))
  },
  {
    title: '状态',
    key: 'status',
    render: row => h(NTag, { bordered: false, type: row.status === 'active' ? 'success' : 'warning' }, { default: () => row.status })
  },
  {
    title: '操作',
    key: 'actions',
    render: row =>
      selectedClass.value?.status === 'dissolved'
        ? h('span', { class: 'text-#94a3b8' }, '班级已解散')
        : h(
            NPopconfirm,
            {
              onPositiveClick: () => removeMember(row.student_id)
            },
            {
              trigger: () => h(NButton, { size: 'small', type: 'error', ghost: true }, { default: () => '移出班级' }),
              default: () => '确认将该学生移出班级？'
            }
          )
  }
];

async function fetchClasses() {
  loading.value = true;
  try {
    const response = await _axios.get<ClassItem[]>('/api/teacher/classes');
    classes.value = response.data;
    if (selectedClass.value) {
      const latest = classes.value.find(item => item.id === selectedClass.value?.id);
      if (!latest) {
        selectedClass.value = null;
      }
    }
  } catch (error: any) {
    console.error('获取教师班级失败:', error);
    window.$message?.error(error?.response?.data?.detail || '获取教师班级失败');
  } finally {
    loading.value = false;
  }
}

async function createClass() {
  try {
    await formRef.value?.validate();
    creating.value = true;
    await _axios.post('/api/teacher/classes', { ...formModel });
    window.$message?.success('班级创建成功');
    formModel.name = '';
    formModel.description = '';
    await fetchClasses();
  } catch (error: any) {
    if (error?.response) {
      window.$message?.error(error.response.data?.detail || '创建班级失败');
    }
  } finally {
    creating.value = false;
  }
}

async function loadClassDetail(classId: string) {
  try {
    const response = await _axios.get<ClassDetail>(`/api/teacher/classes/${classId}`);
    selectedClass.value = response.data;
  } catch (error: any) {
    console.error('获取班级详情失败:', error);
    window.$message?.error(error?.response?.data?.detail || '获取班级详情失败');
  }
}

async function dissolveClass(classId: string) {
  try {
    await _axios.post(`/api/teacher/classes/${classId}/dissolve`);
    window.$message?.success('班级已解散');
    await fetchClasses();
    if (selectedClass.value?.id === classId) {
      await loadClassDetail(classId);
    }
  } catch (error: any) {
    console.error('解散班级失败:', error);
    window.$message?.error(error?.response?.data?.detail || '解散班级失败');
  }
}

async function removeMember(studentId: number) {
  if (!selectedClass.value) return;
  try {
    const response = await _axios.delete<ClassDetail>(`/api/teacher/classes/${selectedClass.value.id}/members/${studentId}`);
    selectedClass.value = response.data;
    await fetchClasses();
    window.$message?.success('已将学生移出班级');
  } catch (error: any) {
    console.error('移出班级成员失败:', error);
    window.$message?.error(error?.response?.data?.detail || '移出班级成员失败');
  }
}

onMounted(fetchClasses);
</script>

<style scoped>
.class-card {
  min-height: 210px;
}
</style>
