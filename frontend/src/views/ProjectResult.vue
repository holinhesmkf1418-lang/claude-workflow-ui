<template>
  <div class="project-result">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <el-result icon="error" title="加载失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
        </template>
      </el-result>
    </div>

    <!-- Content -->
    <template v-else-if="project">
      <!-- PM's soul-searching questions dialog -->
      <QuestionDialog
        :questions="store.pendingQuestions"
        @done="onQuestionsDone"
      />

      <!-- Header -->
      <div class="result-header">
        <div class="header-left">
          <el-button text :icon="ArrowLeft" @click="$router.push('/')" />
          <div>
            <h1 class="project-title">{{ truncate(project.project_idea, 80) }}</h1>
            <div class="project-meta">
              <el-tag :type="statusTag" size="small" effect="dark">
                {{ project.status_detail || project.status }}
              </el-tag>
              <span class="meta-time">创建于 {{ formatTime(project.created_at) }}</span>
            </div>
          </div>
        </div>
        <div class="header-actions">
          <el-popconfirm
            v-if="project.status === 'running' || project.status === 'awaiting_input'"
            title="确定取消 Workflow？"
            confirm-button-text="取消"
            cancel-button-text="不取消"
            @confirm="handleCancel"
          >
            <template #reference>
              <el-button :icon="Remove" type="danger" plain>取消 Workflow</el-button>
            </template>
          </el-popconfirm>
          <el-button :icon="Plus" @click="$router.push('/')">开始新项目</el-button>
        </div>
      </div>

      <!-- Status Timeline -->
      <el-card shadow="never" class="timeline-card" v-if="project.status !== 'completed'">
        <StatusTimeline :steps="timelineSteps" />
      </el-card>

      <!-- Result summary (when completed) -->
      <el-card v-if="project.status === 'completed'" shadow="never" class="summary-card">
        <div class="summary-grid">
          <div class="summary-item">
            <div class="summary-icon" style="background: #e6f7ff; color: #1890ff">📋</div>
            <div class="summary-text">
              <div class="summary-label">需求推演</div>
              <div class="summary-value">✅ 已完成</div>
            </div>
          </div>
          <div class="summary-item">
            <div class="summary-icon" style="background: #f6ffed; color: #52c41a">🏗️</div>
            <div class="summary-text">
              <div class="summary-label">架构设计</div>
              <div class="summary-value">✅ 已完成</div>
            </div>
          </div>
          <div class="summary-item">
            <div class="summary-icon" style="background: #fff7e6; color: #fa8c16">📝</div>
            <div class="summary-text">
              <div class="summary-label">开发计划</div>
              <div class="summary-value">✅ {{ project.tasks.length }} 个 Task</div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- Tabs for content -->
      <el-card shadow="never" class="content-card">
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="📋 需求文档 (PRD)" name="prd">
            <PrdViewer
              :prd="project.prd"
              :loading="isStepActive('prd')"
              :streaming-content="store.streamingContent.prd || undefined"
            />
            <div v-if="isStreaming('prd')" class="streaming-indicator">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>接收中… ({{ store.streamingContent.prd.length }} 字)</span>
            </div>
          </el-tab-pane>

          <el-tab-pane label="🏗️ 架构设计" name="architecture">
            <ArchitectureViewer
              :architecture="project.architecture"
              :loading="isStepActive('architecture')"
              :streaming-content="store.streamingContent.architecture || undefined"
            />
            <div v-if="isStreaming('architecture')" class="streaming-indicator">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>接收中… ({{ store.streamingContent.architecture.length }} 字)</span>
            </div>
          </el-tab-pane>

          <el-tab-pane label="📝 开发计划" name="plan">
            <PlanViewer
              :plan="project.plan"
              :loading="isStepActive('plan')"
              :streaming-content="store.streamingContent.plan || undefined"
            />
            <div v-if="isStreaming('plan')" class="streaming-indicator">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>接收中… ({{ store.streamingContent.plan.length }} 字)</span>
            </div>
          </el-tab-pane>

          <el-tab-pane
            :label="`✅ 任务清单 (${project.tasks.length})`"
            name="tasks"
          >
            <TaskListView
              :tasks="project.tasks"
              :loading="isStepActive('tasks')"
            />
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <!-- Failed state -->
      <el-alert
        v-if="project.status === 'failed'"
        title="Workflow 执行失败"
        :description="project.error || '请检查 API Key 和网络连接'"
        type="error"
        show-icon
        closable
        style="margin-top: 16px"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Plus, Loading, Remove } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useProjectStore } from '@/stores/project'
import { api } from '@/api'
import StatusTimeline from '@/components/StatusTimeline.vue'
import type { TimelineStep } from '@/components/StatusTimeline.vue'
import PrdViewer from '@/components/PrdViewer.vue'
import ArchitectureViewer from '@/components/ArchitectureViewer.vue'
import TaskListView from '@/components/TaskListView.vue'
import PlanViewer from '@/components/PlanViewer.vue'
import QuestionDialog from '@/components/QuestionDialog.vue'

const route = useRoute()
const store = useProjectStore()

const loading = ref(true)
const error = ref('')
const activeTab = ref('prd')

const project = computed(() => store.currentProject)

const statusTag = computed(() => {
  const map: Record<string, string> = {
    completed: 'success',
    running: 'warning',
    awaiting_input: 'warning',
    cancelled: 'info',
    failed: 'danger',
    pending: 'info',
  }
  return map[project.value?.status || ''] || 'info'
})

/** True when a step is actively receiving stream tokens */
function isStreaming(step: string): boolean {
  return store.activeStep === step && store.streamingContent[step]?.length > 0
}

const timelineSteps = computed<TimelineStep[]>(() => {
  const p = project.value
  if (!p) return []

  const statusMap: Record<string, 'pending' | 'active' | 'done' | 'error'> = {
    prd: 'pending',
    architecture: 'pending',
    plan: 'pending',
    tasks: 'pending',
  }

  if (p.status === 'failed') {
    if (p.prd) statusMap.prd = 'done'
    else { statusMap.prd = 'error'; return stepsFromMap(statusMap) }
    if (p.architecture) statusMap.architecture = 'done'
    else { statusMap.architecture = 'error'; return stepsFromMap(statusMap) }
    if (p.plan) statusMap.plan = 'done'
    else { statusMap.plan = 'error'; return stepsFromMap(statusMap) }
    statusMap.tasks = 'error'
    return stepsFromMap(statusMap)
  }

  if (p.prd) statusMap.prd = 'done'
  if (p.architecture) statusMap.architecture = 'done'
  if (p.plan) statusMap.plan = 'done'
  if (p.tasks.length > 0) statusMap.tasks = 'done'

  // Mark the actively streaming step
  if (store.activeStep && statusMap[store.activeStep] === 'pending') {
    statusMap[store.activeStep] = 'active'
  }

  // Fallback: if running, find the active step from DB state
  if (p.status === 'running') {
    if (!p.prd && statusMap.prd !== 'active') statusMap.prd = 'active'
    else if (!p.architecture && statusMap.architecture !== 'active') statusMap.architecture = 'active'
    else if (!p.plan && statusMap.plan !== 'active') statusMap.plan = 'active'
    else if (p.tasks.length === 0 && statusMap.tasks !== 'active') statusMap.tasks = 'active'
  }

  if (p.status === 'completed') {
    statusMap.prd = 'done'
    statusMap.architecture = 'done'
    statusMap.plan = 'done'
    statusMap.tasks = 'done'
  }

  return stepsFromMap(statusMap)
})

function stepsFromMap(m: Record<string, string>): TimelineStep[] {
  return [
    { label: '需求推演', detail: '产品需求文档', status: m.prd as any },
    { label: '架构设计', detail: '技术架构与 claude.md', status: m.architecture as any },
    { label: '开发计划', detail: '结构化计划', status: m.plan as any },
    { label: '生成任务', detail: 'Codex 就绪指令', status: m.tasks as any },
  ]
}

function isStepActive(step: string): boolean {
  if (project.value?.status !== 'running') return false
  // If streaming is actively providing content for this step, don't show loading skeleton
  if (store.activeStep === step && store.streamingContent[step]?.length > 0) return false
  return !project.value?.[step as keyof typeof project.value]
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n) + '…' : s
}

function formatTime(ts: string) {
  return new Date(ts).toLocaleString('zh-CN')
}

function onQuestionsDone() {
  activeTab.value = 'architecture'
}

async function handleCancel() {
  if (!project.value) return
  try {
    await api.cancelProject(project.value.id)
    ElMessage.info('Workflow 已取消')
  } catch (e: any) {
    ElMessage.error(e.message || '取消失败')
  }
}

onMounted(async () => {
  const id = route.params.id as string
  if (!id) {
    error.value = '缺少项目 ID'
    loading.value = false
    return
  }

  try {
    // Try to connect SSE first (if project exists)
    store.connectSSE(id)
    // Also fetch current state
    const p = await api.getProject(id)
    store.currentProject = p
  } catch (e: any) {
    error.value = e.message || '加载项目失败'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  store.disconnectSSE()
})
</script>

<style scoped>
.project-result {
  max-width: 900px;
  margin: 0 auto;
}
.loading-state {
  padding: 48px;
}
.error-state {
  padding: 48px 0;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}
.header-left {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.project-title {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 6px;
  line-height: 1.4;
}
.project-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}
.meta-time {
  font-size: 13px;
  color: #909399;
}
.timeline-card {
  margin-bottom: 16px;
  border-radius: 10px;
}
.summary-card {
  margin-bottom: 16px;
  border-radius: 10px;
}
.summary-grid {
  display: flex;
  gap: 16px;
}
.summary-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 8px;
}
.summary-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.summary-text {
  flex: 1;
}
.summary-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 2px;
}
.summary-value {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.content-card {
  border-radius: 10px;
}
.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
  background: #f5f7fa;
  border-radius: 6px;
}
.streaming-indicator .is-loading {
  animation: spin 1.5s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
