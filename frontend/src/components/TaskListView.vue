<template>
  <div class="task-list-view">
    <div v-if="tasks.length === 0 && loading" class="empty-state">
      <el-empty description="开发计划生成中…" />
    </div>
    <div v-else-if="tasks.length === 0" class="empty-state">
      <el-empty description="暂无 Task 清单" />
    </div>

    <template v-else>
      <!-- Summary bar -->
      <el-alert
        :title="`共 ${tasks.length} 个 Task，分 ${phases.length} 个 Phase`"
        type="success"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />

      <!-- Phase groups -->
      <div v-for="phase in phases" :key="phase" class="phase-group">
        <h3 class="phase-title">{{ phase }}</h3>
        <div v-for="task in tasksInPhase(phase)" :key="task.id" class="task-card">
          <el-card shadow="hover" class="task-card-inner">
            <div class="task-header">
              <div class="task-id-badge">
                <el-tag size="small" type="primary" effect="dark" round>
                  Task {{ task.task_id }}
                </el-tag>
              </div>
              <div class="task-title">{{ task.title }}</div>
            </div>

            <div class="task-meta">
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="目标" min-width="100">
                  {{ task.goal }}
                </el-descriptions-item>
                <el-descriptions-item label="要求">
                  {{ task.requirements }}
                </el-descriptions-item>
                <el-descriptions-item label="验收标准">
                  {{ task.acceptance }}
                </el-descriptions-item>
                <el-descriptions-item v-if="task.constraints" label="约束">
                  {{ task.constraints }}
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <!-- Codex instruction preview & copy -->
            <div class="task-actions">
              <el-button
                type="primary"
                size="small"
                :icon="CopyDocument"
                @click="copyCodex(task)"
              >
                复制 Codex 指令
              </el-button>
              <el-button
                size="small"
                @click="openPreview(task)"
              >
                预览指令
              </el-button>
            </div>
          </el-card>
        </div>
      </div>
    </template>

    <!-- Preview dialog -->
    <el-dialog
      v-model="previewVisible"
      :title="`Task ${previewTask?.task_id}: ${previewTask?.title}`"
      width="80%"
      top="5vh"
      destroy-on-close
    >
      <div class="codex-block">{{ previewTask?.codex_instruction }}</div>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button
          type="primary"
          :icon="CopyDocument"
          @click="copyCurrentPreview"
        >
          复制指令
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import type { TaskItem } from '@/types'

const props = defineProps<{
  tasks: TaskItem[]
  loading?: boolean
}>()

const previewVisible = ref(false)
const previewTask = ref<TaskItem | null>(null)

const phases = computed(() => {
  const set = new Set<string>()
  for (const t of props.tasks) {
    if (t.phase) set.add(t.phase)
  }
  return Array.from(set)
})

function tasksInPhase(phase: string) {
  return props.tasks.filter(t => t.phase === phase)
}

async function copyCodex(task: TaskItem) {
  try {
    await navigator.clipboard.writeText(task.codex_instruction)
    ElMessage.success(`Task ${task.task_id} 指令已复制到剪贴板`)
  } catch {
    ElMessage.error('复制失败，请手动选择后复制')
  }
}

function openPreview(task: TaskItem) {
  previewTask.value = task
  previewVisible.value = true
}

function copyCurrentPreview() {
  if (previewTask.value) {
    copyCodex(previewTask.value)
  }
}
</script>

<style scoped>
.task-list-view {
  padding: 8px 0;
}
.phase-group {
  margin-bottom: 24px;
}
.phase-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
  padding-left: 12px;
  border-left: 3px solid #409eff;
}
.task-card {
  margin-bottom: 12px;
}
.task-card-inner {
  border-radius: 8px;
}
.task-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.task-id-badge {
  flex-shrink: 0;
}
.task-title {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}
.task-meta {
  margin-bottom: 12px;
}
.task-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.empty-state {
  padding: 40px 0;
}
</style>
