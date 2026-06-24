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
          <router-link to="/" class="nav-link">新建项目</router-link>
          <router-link to="/debug" class="nav-link">🐛 调试</router-link>
          <router-link to="/test" class="nav-link">🧪 测试</router-link>
          <router-link to="/audit" class="nav-link">🔍 审计</router-link>
          <router-link to="/design" class="nav-link">🎨 设计</router-link>
        </div>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
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
.app-main {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  padding: 24px;
}
</style>
