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

    <!-- Timeout countdown -->
    <div class="timeout-bar" :class="{ urgent: remaining <= 60 }">
      <el-icon :size="16"><Timer /></el-icon>
      <span>超时自动跳过：<strong>{{ formatTime(remaining) }}</strong></span>
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
import { ref, watch, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Timer } from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'

const props = defineProps<{
  questions: string[]
}>()

const emit = defineEmits<{
  done: []
}>()

const TIMEOUT_SECONDS = 600  // 10 minutes

const store = useProjectStore()
const visible = ref(false)
const submitting = ref(false)
const remaining = ref(TIMEOUT_SECONDS)

let countdownTimer: ReturnType<typeof setInterval> | null = null

const answers = reactive<Record<number, string>>({})

function startCountdown() {
  remaining.value = TIMEOUT_SECONDS
  stopCountdown()
  countdownTimer = setInterval(() => {
    remaining.value--
    if (remaining.value <= 0) {
      stopCountdown()
      handleSkip()
    }
  }, 1000)
}

function stopCountdown() {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

watch(() => props.questions.length, (n) => {
  if (n > 0) {
    visible.value = true
    for (let i = 0; i < n; i++) {
      answers[i] = ''
    }
    startCountdown()
  } else {
    visible.value = false
    stopCountdown()
  }
}, { immediate: true })

async function handleSubmit() {
  if (store.currentProject?.status !== 'awaiting_input') {
    ElMessage.info('项目已完成或已继续，无需重复回答')
    close()
    return
  }

  submitting.value = true
  try {
    const payload: Record<string, string> = {}
    const count = props.questions.length
    for (let i = 0; i < count; i++) {
      payload[String(i)] = answers[i]?.trim() || ''
    }
    await store.submitAnswers(payload)
    ElMessage.success(`已提交 ${count} 个回答，继续架构设计`)
    close()
  } catch (e: any) {
    if (store.currentProject?.status !== 'awaiting_input') {
      ElMessage.info('项目已继续，无需重复回答')
      close()
    } else {
      ElMessage.error(e.message || '提交失败')
    }
  } finally {
    submitting.value = false
  }
}

async function handleSkip() {
  if (store.currentProject?.status !== 'awaiting_input') {
    ElMessage.info('项目已完成或已继续')
    close()
    return
  }

  submitting.value = true
  try {
    const payload: Record<string, string> = {}
    for (let i = 0; i < props.questions.length; i++) {
      payload[String(i)] = ''
    }
    await store.submitAnswers(payload)
    if (remaining.value > 0) {
      ElMessage.info('已跳过追问，继续架构设计')
    } else {
      ElMessage.info('⏰ 追问超时，已自动跳过')
    }
    close()
  } catch (e: any) {
    if (store.currentProject?.status !== 'awaiting_input') {
      close()
    } else {
      ElMessage.error(e.message || '跳过失败')
    }
  } finally {
    submitting.value = false
  }
}

function close() {
  visible.value = false
  stopCountdown()
  emit('done')
}

onUnmounted(() => {
  stopCountdown()
})
</script>

<style scoped>
.dialog-desc {
  font-size: 14px;
  color: #606266;
  margin-bottom: 16px;
  line-height: 1.6;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
}
.timeout-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #909399;
  background: #fff7e6;
  border-radius: 6px;
  border: 1px solid #ffe58f;
  transition: all 0.3s;
}
.timeout-bar.urgent {
  background: #fff2f0;
  border-color: #ffccc7;
  color: #f56c6c;
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
