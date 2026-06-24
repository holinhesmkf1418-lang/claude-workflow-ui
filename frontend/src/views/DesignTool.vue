<template>
  <div class="tool-page">
    <div class="page-header">
      <h1 class="page-title">🎨 前端设计规范</h1>
      <p class="page-subtitle">把自然语言翻译成专业前端指令，升维视觉到 Linear/Apple 质感（提示词⑤）</p>
    </div>

    <el-row :gutter="24" :justify="result ? 'start' : 'center'">
      <el-col :span="result ? 12 : 14">
        <el-card shadow="never" class="form-card">
          <el-form label-position="top">
            <el-form-item label="页面/组件描述" required>
              <el-input v-model="description" type="textarea" :rows="8" placeholder="描述你要实现的功能和想要的风格。&#10;例：做一个报价单列表页，卡片式布局，每行显示客户名、金额、状态、操作按钮，要求简洁专业" />
            </el-form-item>

            <el-form-item label="技术栈（默认 Vue 3 + Element Plus + TS）">
              <el-input v-model="techStack" placeholder="Vue 3 + TypeScript + Element Plus" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" size="large" :loading="loading" :disabled="!description.trim()" @click="handleSubmit">
                {{ loading ? '生成中…' : '🎨 生成设计指令' }}
              </el-button>
              <el-button v-if="result" size="large" @click="resetForm">清空重来</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col v-if="result" :span="12">
        <el-card shadow="never" class="result-card">
          <template #header><span class="result-title">设计指令</span></template>
          <div class="codex-block">{{ result.instruction }}</div>
          <el-button type="primary" size="large" :icon="CopyDocument" class="copy-btn" @click="copyResult">复制设计指令到 Codex</el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import { api } from '@/api'

const description = ref('')
const techStack = ref('Vue 3 + TypeScript + Element Plus')
const loading = ref(false)
const result = ref<{ instruction: string } | null>(null)

async function handleSubmit() {
  if (!description.value.trim()) return
  loading.value = true
  try {
    result.value = await api.toolGenerate('design', description.value, undefined, techStack.value)
    ElMessage.success('设计指令已生成')
  } catch (e: any) {
    ElMessage.error(e.message || '生成失败')
  } finally { loading.value = false }
}
function resetForm() { description.value = ''; result.value = null }
async function copyResult() {
  if (!result.value?.instruction) return
  await navigator.clipboard.writeText(result.value.instruction)
  ElMessage.success('已复制')
}
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
