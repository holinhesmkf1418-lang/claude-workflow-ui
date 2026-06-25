<template>
  <el-dialog
    v-model="visible"
    title="💬 PM 的灵魂追问"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    width="640px"
    top="8vh"
    class="question-dialog"
  >
    <div class="dialog-desc">
      PRD 需求推演已完成。架构师在继续设计前，有以下问题需要你确认：
    </div>

    <div class="question-list">
      <div
        v-for="(q, idx) in questions"
        :key="idx"
        class="question-item"
      >
        <div class="question-label">
          <el-tag size="small" type="warning" round>追问 {{ idx + 1 }}</el-tag>
          <span class="question-text">{{ q }}</span>
        </div>
        <el-input
          v-model="answers[idx]"
          :rows="3"
          type="textarea"
          :placeholder="'你的回答…（可留空跳过）'"
          maxlength="2000"
          show-word-limit
          :disabled="submitting"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button
          plain
          :disabled="submitting"
          @click="handleSkip"
        >
          跳过（不回答继续）
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="submitting"
          @click="handleSubmit"
        >
          {{ submitting ? '提交中…' : '✅ 回答完毕，继续架构设计' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useProjectStore } from '@/stores/project'

const props = defineProps<{
  questions: string[]
}>()

const emit = defineEmits<{
  done: []
}>()

const store = useProjectStore()
const visible = ref(false)
const submitting = ref(false)

// Reactive dict for form inputs
const answers = reactive<Record<number, string>>({})

watch(() => props.questions.length, (n) => {
  if (n > 0) {
    visible.value = true
    // Initialize empty answers
    for (let i = 0; i < n; i++) {
      answers[i] = ''
    }
  } else {
    visible.value = false
  }
}, { immediate: true })

async function handleSubmit() {
  // Safety: if project is no longer awaiting input, just close
  if (store.currentProject?.status !== 'awaiting_input') {
    ElMessage.info('项目已完成或已继续，无需重复回答')
    visible.value = false
    emit('done')
    return
  }

  submitting.value = true
  try {
    const payload: Record<string, string> = {}
    for (let i = 0; i < props.questions.length; i++) {
      payload[String(i)] = answers[i]?.trim() || ''
    }
    await store.submitAnswers(payload)
    ElMessage.success(`已提交 ${props.questions.length} 个回答，继续架构设计`)
    visible.value = false
    emit('done')
  } catch (e: any) {
    // If the project was already resumed, just close gracefully
    if (store.currentProject?.status !== 'awaiting_input') {
      ElMessage.info('项目已继续，无需重复回答')
      visible.value = false
      emit('done')
    } else {
      ElMessage.error(e.message || '提交失败')
    }
  } finally {
    submitting.value = false
  }
}

async function handleSkip() {
  // Safety: if project is no longer awaiting input, just close
  if (store.currentProject?.status !== 'awaiting_input') {
    ElMessage.info('项目已完成或已继续')
    visible.value = false
    emit('done')
    return
  }

  submitting.value = true
  try {
    const payload: Record<string, string> = {}
    for (let i = 0; i < props.questions.length; i++) {
      payload[String(i)] = ''
    }
    await store.submitAnswers(payload)
    ElMessage.info('已跳过追问，继续架构设计')
    visible.value = false
    emit('done')
  } catch (e: any) {
    // If the project was already resumed, just close gracefully
    if (store.currentProject?.status !== 'awaiting_input') {
      ElMessage.info('项目已继续')
      visible.value = false
      emit('done')
    } else {
      ElMessage.error(e.message || '跳过失败')
    }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.dialog-desc {
  font-size: 14px;
  color: #606266;
  margin-bottom: 20px;
  line-height: 1.6;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
}
.question-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.question-item {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.question-label {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 12px;
}
.question-text {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
  line-height: 1.5;
}
.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
