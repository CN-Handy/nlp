import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * 观战模式下，游戏状态完全由 WebSocket 事件驱动。
 * 此 store 仅保留连接状态管理。
 */
export const useGameStore = defineStore('game', () => {
  const connected = ref(false)
  const error = ref<string | null>(null)

  function setConnected(value: boolean) {
    connected.value = value
  }

  function setError(msg: string | null) {
    error.value = msg
  }

  return {
    connected,
    error,
    setConnected,
    setError,
  }
})
