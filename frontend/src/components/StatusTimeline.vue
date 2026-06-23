<template>
  <div class="status-timeline">
    <div
      v-for="(step, idx) in steps"
      :key="idx"
      class="step-item"
      :class="{
        'is-active': step.status === 'active',
        'is-done': step.status === 'done',
        'is-pending': step.status === 'pending',
        'is-error': step.status === 'error',
      }"
    >
      <div class="step-indicator">
        <el-icon v-if="step.status === 'done'" color="#67c23a" :size="20">
          <CircleCheckFilled />
        </el-icon>
        <el-icon v-else-if="step.status === 'error'" color="#f56c6c" :size="20">
          <CircleCloseFilled />
        </el-icon>
        <el-icon v-else-if="step.status === 'active'" color="#409eff" :size="20" class="spin-icon">
          <Loading />
        </el-icon>
        <span v-else class="step-dot"></span>
      </div>
      <div class="step-content">
        <div class="step-label">{{ step.label }}</div>
        <div v-if="step.detail" class="step-detail">{{ step.detail }}</div>
      </div>
      <div v-if="idx < steps.length - 1" class="step-line"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CircleCheckFilled, CircleCloseFilled, Loading } from '@element-plus/icons-vue'

export interface TimelineStep {
  label: string
  detail?: string
  status: 'pending' | 'active' | 'done' | 'error'
}

defineProps<{
  steps: TimelineStep[]
}>()
</script>

<style scoped>
.status-timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 8px 0;
}
.step-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  position: relative;
  min-height: 48px;
}
.step-indicator {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}
.step-dot {
  display: block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #dcdfe6;
  border: 2px solid #dcdfe6;
}
.step-item.is-active .step-dot {
  background: #409eff;
  border-color: #409eff;
}
.step-item.is-done .step-dot {
  background: #67c23a;
  border-color: #67c23a;
}
.step-content {
  flex: 1;
  padding-bottom: 16px;
}
.step-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}
.step-detail {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}
.step-item.is-active .step-label {
  color: #409eff;
  font-weight: 600;
}
.step-item.is-done .step-label {
  color: #67c23a;
}
.step-item.is-error .step-label {
  color: #f56c6c;
}
.step-line {
  position: absolute;
  left: 11px;
  top: 28px;
  bottom: 0;
  width: 2px;
  background: #e4e7ed;
}
.step-item.is-done .step-line {
  background: #67c23a;
}
.step-item.is-active .step-line {
  background: #409eff;
}
.spin-icon {
  animation: spin 1.5s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
