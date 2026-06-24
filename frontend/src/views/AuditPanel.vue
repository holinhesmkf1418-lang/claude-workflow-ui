<template>
  <div class="tool-page">
    <div class="page-header">
      <h1 class="page-title">🔍 代码审计</h1>
      <p class="page-subtitle">贴入需要审查的代码，大脑按提示词③扫描巨石文件、硬编码、静默失败等问题</p>
    </div>

    <el-row :gutter="24" :justify="result ? 'start' : 'center'">
      <el-col :span="result ? 12 : 14">
        <el-card shadow="never" class="form-card">
          <el-form label-position="top">
            <el-form-item label="关联项目（可选）">
              <el-select v-model="projectId" placeholder="选项目自动注入架构上下文" clearable filterable style="width:100%">
                <el-option v-for="p in projects" :key="p.id" :label="truncate(p.project_idea, 60)" :value="p.id" />
              </el-select>
            </el-form-item>

            <el-form-item label="代码 / 文件路径" required>
              <el-input v-model="codeInput" type="textarea" :rows="10" placeholder="粘贴代码片段，或描述你要审查的文件路径（如 src/components/QuoteForm.vue）" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" size="large" :loading="loading" :disabled="!codeInput.trim()" @click="handleSubmit">
                {{ loading ? '审计中…' : '🔍 开始审计' }}
              </el-button>
              <el-button v-if="result" size="large" @click="resetForm">清空重来</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col v-if="result" :span="12">
        <el-card shadow="never" class="result-card">
          <template #header><span class="result-title">审计结果</span></template>
          <div class="codex-block">{{ result.instruction }}</div>
          <el-button type="primary" size="large" :icon="CopyDocument" class="copy-btn" @click="copyResult">复制审计指令到 Codex</el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import { api } from '@/api'
import type { ProjectListItem } from '@/types'

const codeInput = ref('')
const projectId = ref('')
const loading = ref(false)
const result = ref<{ instruction: string } | null>(null)
const projects = ref<ProjectListItem[]>([])

async function handleSubmit() {
  if (!codeInput.value.trim()) return
  loading.value = true
  try {
    result.value = await api.toolGenerate('audit', codeInput.value, projectId.value || undefined)
    ElMessage.success('审计完成')
  } catch (e: any) {
    ElMessage.error(e.message || '审计失败')
  } finally { loading.value = false }
}
function resetForm() { codeInput.value = ''; projectId.value = ''; result.value = null }
async function copyResult() {
  if (!result.value?.instruction) return
  await navigator.clipboard.writeText(result.value.instruction)
  ElMessage.success('已复制')
}
function truncate(s: string, n: number) { return s.length > n ? s.slice(0, n) + '…' : s }

onMounted(async () => {
  try { projects.value = await api.listProjects() } catch { /* */ }
})
</script>

<style scoped>
.tool-page { max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; color: #1a1a2e; margin-bottom: 8px; }
.page-subtitle { font-size: 14px; color: #909399; }
.form-card, .result-card { border-radius: 10px; }
.result-title { font-size: 15px; font-weight: 600; }
.codex-block {
  background: #1e1e2e; color: #cdd6f4; padding: 16px; border-radius: 8px;
  font-family: "SF Mono", "Menlo", "Monaco", "Consolas", monospace;
  font-size: 13px; line-height: 1.5; white-space: pre-wrap;
  overflow-x: auto; max-height: 500px; overflow-y: auto; margin-bottom: 12px;
}
.copy-btn { width: 100%; }
</style>
