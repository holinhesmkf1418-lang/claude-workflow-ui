<template>
  <div class="test-page">
    <div class="page-header">
      <h1 class="page-title">🧪 测试指令生成</h1>
      <p class="page-subtitle">
        描述你要测的场景，大脑按提示词⑥生成完整测试指令，复制到 Codex 即可执行
      </p>
    </div>

    <el-row :gutter="24" :justify="result ? 'start' : 'center'">
      <!-- Input -->
      <el-col :span="result ? 12 : 14">
        <el-card shadow="never" class="form-card">
          <el-form label-position="top">
            <el-form-item label="关联项目（可选，注入上下文让测试更准）">
              <el-select
                v-model="selectedProjectId"
                placeholder="选项目后自动注入架构和PRD上下文"
                clearable
                filterable
                style="width:100%"
              >
                <el-option
                  v-for="p in projects"
                  :key="p.id"
                  :label="truncate(p.project_idea, 60)"
                  :value="p.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="测试场景" required>
              <el-input
                v-model="scenario"
                type="textarea"
                :rows="8"
                placeholder="例：验证报价单完整流程 —— 用户选择产品、填入数量、切换币种、点击生成报价单，验证 PDF 下载按钮出现。"
              />
            </el-form-item>

            <!-- Optional add-ons -->
            <el-divider content-position="left">按需附加</el-divider>
            <el-checkbox v-model="withAudit" label="测试完成后执行代码审计（提示词③）" border size="large" style="width:100%; margin-bottom:12px" />
            <el-checkbox v-model="withDesign" label="应用前端设计规范提升UI质感（提示词⑤）" border size="large" style="width:100%; margin-bottom:16px" />

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="loading"
                :disabled="!scenario.trim()"
                @click="handleGenerate"
              >
                {{ loading ? '生成中…' : '🧪 生成测试指令' }}
              </el-button>
              <el-button
                v-if="result"
                size="large"
                @click="resetForm"
              >清空重来</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- Result -->
      <el-col v-if="result" :span="12">
        <el-card shadow="never" class="result-card">
          <template #header>
            <div class="result-header">
              <span class="result-title">测试指令</span>
              <el-tag type="success" size="large" effect="dark">就绪</el-tag>
            </div>
          </template>

          <div class="result-section">
            <div class="section-label">已附加</div>
            <div class="addon-tags">
              <el-tag type="info" size="small" effect="plain">提示词⑥ 测试生成</el-tag>
              <el-tag v-if="withAudit" type="warning" size="small" effect="plain">+ 提示词③ 代码审计</el-tag>
              <el-tag v-if="withDesign" type="success" size="small" effect="plain">+ 提示词⑤ 前端设计</el-tag>
            </div>
          </div>

          <div class="result-section">
            <div class="section-label">指令内容（复制后粘贴到 Codex）</div>
            <div class="codex-block">{{ result.instruction }}</div>
          </div>

          <el-button
            type="primary"
            size="large"
            :icon="CopyDocument"
            class="copy-btn"
            @click="copyInstruction"
          >
            复制指令到 Codex
          </el-button>
        </el-card>
      </el-col>
    </el-row>

    <!-- How to use -->
    <el-card v-if="!result" shadow="never" class="help-card">
      <template #header><span>使用流程</span></template>
      <el-steps :active="4" align-center>
        <el-step title="描述场景" description="告诉大脑要测什么" />
        <el-step title="按需附加" description="勾选审计/设计规范" />
        <el-step title="生成指令" description="大脑出完整测试方案" />
        <el-step title="粘贴Codex" description="Codex 写脚本→跑→自愈" />
      </el-steps>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import { api } from '@/api'
import type { ProjectListItem } from '@/types'

const scenario = ref('')
const selectedProjectId = ref('')
const withAudit = ref(false)
const withDesign = ref(false)
const loading = ref(false)
const result = ref<{ instruction: string } | null>(null)
const projects = ref<ProjectListItem[]>([])

async function handleGenerate() {
  if (!scenario.value.trim()) return
  loading.value = true
  try {
    result.value = await api.testGenerate(
      scenario.value,
      selectedProjectId.value || undefined,
      withAudit.value,
      withDesign.value,
    )
    ElMessage.success('测试指令已生成')
  } catch (e: any) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  scenario.value = ''
  selectedProjectId.value = ''
  withAudit.value = false
  withDesign.value = false
  result.value = null
}

async function copyInstruction() {
  if (!result.value?.instruction) return
  try {
    await navigator.clipboard.writeText(result.value.instruction)
    ElMessage.success('指令已复制，粘贴到 Codex 执行')
  } catch {
    ElMessage.error('复制失败')
  }
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n) + '…' : s
}

onMounted(async () => {
  try {
    projects.value = await api.listProjects()
  } catch { /* silent */ }
})
</script>

<style scoped>
.test-page {
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  text-align: center;
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
.form-card,
.result-card {
  border-radius: 10px;
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
  margin-bottom: 8px;
}
.addon-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
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
  max-height: 500px;
  overflow-y: auto;
}
.copy-btn {
  width: 100%;
  margin-top: 8px;
}
.help-card {
  margin-top: 24px;
  border-radius: 10px;
}
</style>
