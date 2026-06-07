import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/game/:roomId',
      name: 'game',
      component: () => import('@/views/GameView.vue'),
      props: true,
    },
  ],
})

export default router
