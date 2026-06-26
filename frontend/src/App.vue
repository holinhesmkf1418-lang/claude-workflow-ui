<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-inner">
        <router-link to="/" class="logo">
          <el-icon :size="24" color="#409eff"><Promotion /></el-icon>
          <span class="logo-text">Workflow Web UI</span>
        </router-link>
        <el-tag type="info" size="small" effect="plain">Claude Code Workflow 可视化面板</el-tag>
        <div class="nav-links">
          <router-link to="/" class="nav-link">🏠 首页</router-link>
          <router-link to="/debug" class="nav-link">🐛 调试</router-link>
          <router-link to="/test" class="nav-link">🧪 测试</router-link>
          <router-link to="/audit" class="nav-link">🔍 审计</router-link>
          <router-link to="/design" class="nav-link">🎨 设计</router-link>
        </div>
        <!-- SSE connection indicator -->
        <div class="connection-indicator" :class="{ connected: store.isStreaming }">
          <span class="dot"></span>
          <span class="label">{{ store.isStreaming ? '已连接' : '未连接' }}</span>
        </div>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useProjectStore } from '@/stores/project'

const store = useProjectStore()
</script>

<style scoped>
.app-container {
  min-height: 100vh;
}
.app-header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  height: 60px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.logo-text {
  background: linear-gradient(135deg, #409eff, #6366f1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.nav-links {
  flex: 1;
  display: flex;
  justify-content: center;
  gap: 28px;
}
.nav-link {
  text-decoration: none;
  color: #606266;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.2s;
}
.nav-link:hover {
  color: #409eff;
}
.connection-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 20px;
  background: #f5f7fa;
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  transition: all 0.3s;
}
.connection-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c4cc;
  transition: background 0.3s;
}
.connection-indicator.connected {
  background: #e6f7e6;
  color: #67c23a;
}
.connection-indicator.connected .dot {
  background: #67c23a;
  box-shadow: 0 0 4px rgba(103, 194, 58, 0.5);
}
.app-main {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  padding: 24px;
}
</style>
