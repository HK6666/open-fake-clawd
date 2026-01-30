import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Sessions from '../views/Sessions.vue'
import SessionDetail from '../views/SessionDetail.vue'
import Memory from '../views/Memory.vue'
import Settings from '../views/Settings.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard
    },
    {
      path: '/sessions',
      name: 'sessions',
      component: Sessions
    },
    {
      path: '/sessions/:id',
      name: 'session-detail',
      component: SessionDetail
    },
    {
      path: '/memory',
      name: 'memory',
      component: Memory
    },
    {
      path: '/settings',
      name: 'settings',
      component: Settings
    }
  ]
})

export default router
