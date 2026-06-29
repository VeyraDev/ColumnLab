import { createRouter, createWebHistory } from 'vue-router'
import { TOKEN_KEY } from '@/types/api'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/workspace',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/imports',
      name: 'imports',
      component: () => import('@/views/ImportView.vue'),
    },
    {
      path: '/workspace/:datasetId?',
      name: 'workspace',
      component: () => import('@/views/WorkspaceView.vue'),
    },
    {
      path: '/query/:datasetId?',
      name: 'query',
      component: () => import('@/views/QueryView.vue'),
    },
    {
      path: '/compression-lab/:datasetId?',
      name: 'compression-lab',
      component: () => import('@/views/CompressionLabView.vue'),
    },
    {
      path: '/benchmarks',
      name: 'benchmarks',
      component: () => import('@/views/BenchmarkView.vue'),
    },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!to.meta.public && !token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && token) {
    return { name: 'workspace' }
  }
  return true
})

export default router
