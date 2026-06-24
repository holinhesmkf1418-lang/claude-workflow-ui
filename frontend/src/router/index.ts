import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'new-project',
      component: () => import('@/views/NewProject.vue'),
    },
    {
      path: '/debug',
      name: 'debug',
      component: () => import('@/views/DebugPanel.vue'),
    },
    {
      path: '/test',
      name: 'test',
      component: () => import('@/views/TestGenerator.vue'),
    },
    {
      path: '/audit',
      name: 'audit',
      component: () => import('@/views/AuditPanel.vue'),
    },
    {
      path: '/design',
      name: 'design',
      component: () => import('@/views/DesignTool.vue'),
    },
    {
      path: '/projects/:id',
      name: 'project-result',
      component: () => import('@/views/ProjectResult.vue'),
      props: true,
    },
  ],
})

export default router
