<template>
  <div class="new-project-page">
    <div class="hero">
      <h1 class="hero-title">🚀 启动新项目</h1>
      <p class="hero-subtitle">
        输入你的项目想法，Workflow 将自动完成需求推演 → 架构设计 → 生成 Codex 就绪的 Task 清单
      </p>
    </div>

    <el-card shadow="never" class="form-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="项目想法" prop="projectIdea">
          <el-input
            v-model="form.projectIdea"
            type="textarea"
            :rows="6"
            placeholder="例如：做一个自由职业者报价单工具，支持模板管理、汇率换算、PDF 导出…"
            maxlength="10000"
            show-word-limit
          />
        </el-form-item>

        <el-divider content-position="left">可选配置</el-divider>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="AI 模型">
              <el-select v-model="form.model" placeholder="默认模型" clearable style="width:100%">
                <el-option label="deepseek-v4-flash (快速)" value="deepseek-v4-flash" />
                <el-option label="deepseek-v4-pro (强力)" value="deepseek-v4-pro" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="项目目录">
              <el-input v-model="form.projectDir" placeholder="./" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="GitHub 仓库">
              <el-input v-model="form.githubRepo" placeholder="（可选）" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item class="form-actions">
          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            :icon="Promotion"
            @click="handleSubmit"
          >
            {{ submitting ? 'Workflow 执行中…' : '🚀 启动 Workflow' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Recent projects -->
    <div class="recent-section" v-if="filteredProjects.length > 0 || searchQuery">
      <div class="section-header">
        <h2 class="section-title">项目列表</h2>
        <el-input
          v-model="searchQuery"
          class="search-input"
          placeholder="搜索项目…"
          clearable
          prefix-icon="Search"
          size="small"
        />
      </div>
      <el-timeline>
        <el-timeline-item
          v-for="p in filteredProjects"
          :key="p.id"
          :timestamp="formatTime(p.created_at)"
          :color="statusColor(p.status)"
        >
          <div class="project-row">
            <div class="project-info">
              <el-link type="primary" @click="$router.push(`/projects/${p.id}`)">
                {{ truncate(p.project_idea, 60) }}
              </el-link>
              <el-tag :type="statusTag(p.status)" size="small" style="margin-left: 8px">
                {{ p.status_detail || p.status }}
              </el-tag>
            </div>
            <el-popconfirm
              title="确定删除此项目？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(p.id)"
            >
              <template #reference>
                <el-button
                  text
                  size="small"
                  type="danger"
                  :icon="Delete"
                  :loading="deletingId === p.id"
                />
              </template>
            </el-popconfirm>
          </div>
        </el-timeline-item>
      </el-timeline>
      <div v-if="filteredProjects.length === 0 && searchQuery" class="no-results">
        没有找到匹配的项目
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Promotion, Delete } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useProjectStore } from '@/stores/project'
import type { ProjectListItem } from '@/types'
import { api } from '@/api'

const router = useRouter()
const store = useProjectStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const recentProjects = ref<ProjectListItem[]>([])
const searchQuery = ref('')
const deletingId = ref<string | null>(null)

const form = ref({
  projectIdea: '',
  model: '',
  projectDir: './',
  githubRepo: '',
})

const rules: FormRules = {
  projectIdea: [
    { required: true, message: '请填写项目想法', trigger: 'blur' },
    { min: 10, message: '至少 10 个字符，描述清晰一些效果更好', trigger: 'blur' },
  ],
}

const filteredProjects = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return recentProjects.value
  return recentProjects.value.filter(p =>
    p.project_idea.toLowerCase().includes(q)
  )
})

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const project = await store.createAndWatch(
      form.value.projectIdea,
      form.value.model || undefined,
      form.value.githubRepo || undefined,
      form.value.projectDir || undefined,
    )
    ElMessage.success('Workflow 已启动！正在跳转…')
    router.push(`/projects/${project.id}`)
  } catch (e: any) {
    ElMessage.error(e.message || '启动失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: string) {
  deletingId.value = id
  try {
    await api.deleteProject(id)
    recentProjects.value = recentProjects.value.filter(p => p.id !== id)
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  } finally {
    deletingId.value = null
  }
}

function statusColor(status: string) {
  const map: Record<string, string> = {
    completed: '#67c23a',
    running: '#409eff',
    failed: '#f56c6c',
    pending: '#909399',
  }
  return map[status] || '#909399'
}

function statusTag(status: string) {
  const map: Record<string, string> = {
    completed: 'success',
    running: 'primary',
    failed: 'danger',
    pending: 'info',
  }
  return map[status] || 'info'
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n) + '…' : s
}

function formatTime(ts: string) {
  const d = new Date(ts)
  return d.toLocaleString('zh-CN')
}

async function loadProjects() {
  try {
    recentProjects.value = await api.listProjects()
  } catch { /* silent */ }
}

onMounted(loadProjects)
</script>

<style scoped>
.new-project-page {
  max-width: 720px;
  margin: 0 auto;
}
.hero {
  text-align: center;
  margin-bottom: 32px;
}
.hero-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 12px;
}
.hero-subtitle {
  font-size: 15px;
  color: #909399;
  line-height: 1.6;
  max-width: 520px;
  margin: 0 auto;
}
.form-card {
  border-radius: 12px;
}
.form-actions {
  margin-top: 8px;
  margin-bottom: 0;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 32px 0 16px;
}
.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}
.search-input {
  width: 200px;
}
.project-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.project-info {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}
.no-results {
  text-align: center;
  color: #909399;
  padding: 24px 0;
  font-size: 14px;
}
</style>
