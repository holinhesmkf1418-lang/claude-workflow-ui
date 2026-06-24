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
      path: '/projects/:id',
      name: 'project-result',
      component: () => import('@/views/ProjectResult.vue'),
      props: true,
    },
  ],
})

export default router
