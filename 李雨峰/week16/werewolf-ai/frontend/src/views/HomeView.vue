<template>
  <div class="home-view">
    <div class="home-container">
      <div class="home-header">
        <h1 class="game-title">狼人杀 AI</h1>
        <p class="game-subtitle">AI 驱动的狼人杀观战系统</p>
      </div>

      <div class="action-area">
        <el-button
          type="primary"
          size="large"
          class="start-btn"
          :loading="loading"
          @click="handleStartGame"
        >
          <el-icon><VideoPlay /></el-icon>
          开始游戏（上帝视角观战）
        </el-button>
        <p class="hint">点击后将自动创建 9 人 AI 对局，你可以观战所有事件</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { quickStart } from '@/api/http'

const router = useRouter()
const loading = ref(false)

async function handleStartGame() {
  loading.value = true
  try {
    const result = await quickStart()
    ElMessage.success('游戏已创建，正在进入观战...')
    router.push({
      name: 'game',
      params: { roomId: result.room_id },
    })
  } catch {
    ElMessage.error('创建游戏失败，请检查后端是否运行')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.home-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.home-container {
  width: 100%;
  max-width: 520px;
  text-align: center;
}

.home-header {
  margin-bottom: 48px;
}

.game-title {
  font-size: 48px;
  font-weight: 800;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 12px;
}

.game-subtitle {
  font-size: 16px;
  color: #888;
  margin: 0;
}

.action-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.start-btn {
  width: 320px;
  height: 56px;
  font-size: 18px;
  font-weight: 600;
  border-radius: 12px;
}

.hint {
  font-size: 13px;
  color: #666;
  margin: 0;
}
</style>
