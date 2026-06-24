<template>
  <div class="debug-page">
    <div class="page-header">
      <h1 class="page-title">🐛 BUG 调试调度引擎</h1>
      <p class="page-subtitle">
        把 Codex 的报错日志贴进来，大脑帮你分析根因，输出精准修复指令
      </p>
    </div>

    <el-row :gutter="24">
      <!-- Input area -->
      <el-col :span="result ? 12 : 16">
        <el-card shadow="never" class="input-card">
          <el-form label-position="top">
            <el-form-item label="关联项目（可选 — 选择后自动注入项目上下文，分析更精准）">
              <el-select
                v-model="selectedProjectId"
                placeholder="不选也可以分析，但关联项目后结果更准"
                clearable
                filterable
                style="width:100%"
              >
                <el-option
                  v-for="p in projects"
                  :key="p.id"
                  :label="truncate(p.project_idea, 60)"
                  :value="p.id"
                >
                  <span>{{ truncate(p.project_idea, 60) }}</span>
                  <el-tag
                    :type="statusTag(p.status)"
                    size="small"
                    style="margin-left: 8px; float: right"
                  >{{ p.status }}</el-tag>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="报错日志" required>
              <el-input
                v-model="errorLog"
                type="textarea"
                :rows="10"
                placeholder="粘贴 Codex 终端里的完整报错日志…"
              />
            </el-form-item>

            <el-form-item label="代码上下文（可选，有助于 PROBE 阶段定位）">
              <el-input
                v-model="codeContext"
                type="textarea"
                :rows="5"
                placeholder="相关文件的代码片段、函数名、行号等…"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="loading"
                :disabled="!errorLog.trim()"
                @click="handleAnalyze"
              >
                {{ loading ? '分析中…' : '🔍 开始诊断' }}
              </el-button>
              <el-button
                v-if="result"
                size="large"
                @click="resetForm"
              >
                清空重来
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- Result area -->
      <el-col v-if="result" :span="12">
        <el-card shadow="never" class="result-card">
          <template #header>
            <div class="result-header">
              <span class="result-title">诊断结果</span>
              <el-tag
                :type="stateTagType"
                size="large"
                effect="dark"
              >
                {{ result.state }}
              </el-tag>
            </div>
          </template>

          <!-- Root cause -->
          <div class="result-section">
            <div class="section-label">根因分析</div>
            <el-alert
              :title="result.root_cause"
              :type="stateTagType"
              :closable="false"
              show-icon
            />
          </div>

          <!-- Risk -->
          <div v-if="result.risk" class="result-section">
            <div class="section-label">风险提示</div>
            <el-alert
              :title="result.risk"
              type="warning"
              :closable="false"
              show-icon
            />
          </div>

          <!-- Explanation -->
          <div v-if="result.explanation" class="result-section">
            <div class="section-label">说明</div>
            <p class="explanation-text">{{ result.explanation }}</p>
          </div>

          <!-- Machine instruction -->
          <div v-if="result.machine_instruction" class="result-section">
            <div class="section-label">修复指令（复制后粘贴到 Codex）</div>
            <div class="instruction-block">
              <pre class="codex-block">{{ result.machine_instruction }}</pre>
            </div>
            <el-button
              type="primary"
              :icon="CopyDocument"
              class="copy-btn"
              @click="copyInstruction"
            >
              复制指令到 Codex
            </el-button>
          </div>

          <!-- Gate hint -->
          <el-alert
            v-if="result.state === 'GATE'"
            title="状态为 GATE — 涉及大重构，确认后再执行"
            type="warning"
            show-icon
            :closable="false"
            style="margin-top: 12px"
          />
          <el-alert
            v-if="result.state === 'PROBE'"
            title="状态为 PROBE — 需要更多信息，补全上下文后重新诊断"
            type="info"
            show-icon
            :closable="false"
            style="margin-top: 12px"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- State legend -->
    <el-card v-if="!result" shadow="never" class="legend-card">
      <template #header><span>状态说明</span></template>
      <el-row :gutter="16">
        <el-col :span="6" v-for="item in legend" :key="item.state">
          <div class="legend-item">
            <el-tag :type="item.type" size="small" effect="dark">{{ item.state }}</el-tag>
            <span class="legend-desc">{{ item.desc }}</span>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import { api } from '@/api'
import type { ProjectListItem } from '@/types'

const errorLog = ref('')
const codeContext = ref('')
const loading = ref(false)
const selectedProjectId = ref('')
const projects = ref<ProjectListItem[]>([])

const result = ref<{
  state: string
  root_cause: string
  risk: string
  machine_instruction: string
  explanation: string
  raw: string
} | null>(null)

const stateTagType = computed(() => {
  const map: Record<string, string> = {
    PROBE: 'info',
    SURGERY: 'primary',
    GATE: 'warning',
    VERIFY: 'success',
  }
  return map[result.value?.state || ''] || 'info'
})

const legend = [
  { state: 'PROBE', type: 'info', desc: '缺信息，需要进一步搜索代码' },
  { state: 'SURGERY', type: 'primary', desc: '已锁定，出精准局部修复指令' },
  { state: 'GATE', type: 'warning', desc: '涉及大重构，需你确认' },
  { state: 'VERIFY', type: 'success', desc: '已完成，输出回归验证边界' },
]

async function handleAnalyze() {
  if (!errorLog.value.trim()) return
  loading.value = true
  try {
    result.value = await api.debugAnalyze(
      errorLog.value,
      codeContext.value,
      selectedProjectId.value || undefined,
    )
    ElMessage.success('诊断完成')
  } catch (e: any) {
    ElMessage.error(e.message || '诊断失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  errorLog.value = ''
  codeContext.value = ''
  selectedProjectId.value = ''
  result.value = null
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n) + '…' : s
}

function statusTag(status: string) {
  const map: Record<string, string> = {
    completed: 'success',
    running: 'warning',
    failed: 'danger',
    pending: 'info',
  }
  return map[status] || 'info'
}

onMounted(async () => {
  try {
    projects.value = await api.listProjects()
  } catch { /* silent */ }
})

async function copyInstruction() {
  if (!result.value?.machine_instruction) return
  try {
    await navigator.clipboard.writeText(result.value.machine_instruction)
    ElMessage.success('修复指令已复制，粘贴到 Codex 执行')
  } catch {
    ElMessage.error('复制失败，请手动选择后复制')
  }
}
</script>

<style scoped>
.debug-page {
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  margin-bottom: 24px;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 8px;
}
.page-subtitle {
  font-size: 14px;
  color: #909399;
}
.input-card,
.result-card {
  border-radius: 10px;
  height: 100%;
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.result-title {
  font-size: 15px;
  font-weight: 600;
}
.result-section {
  margin-bottom: 16px;
}
.section-label {
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 6px;
}
.explanation-text {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}
.instruction-block {
  margin-bottom: 8px;
}
.codex-block {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 16px;
  border-radius: 8px;
  font-family: "SF Mono", "Menlo", "Monaco", "Consolas", monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}
.copy-btn {
  width: 100%;
}
.legend-card {
  margin-top: 24px;
  border-radius: 10px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.legend-desc {
  font-size: 13px;
  color: #606266;
}
</style>
