<template>
  <div :class="['phase-banner', `phase-${phase.toLowerCase()}`]">
    <div class="phase-icon">
      <el-icon :size="32">
        <component :is="phaseIcon" />
      </el-icon>
    </div>
    <div class="phase-info">
      <h3 class="phase-title">{{ phaseLabel }}</h3>
      <p class="phase-subtitle">{{ phaseDescription }}</p>
    </div>
    <div v-if="day > 0" class="phase-day">
      <el-tag type="info" size="large">
        第 {{ day }} 天
      </el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Moon, Sunny, ChatDotRound, Trophy, Select } from '@element-plus/icons-vue'
import type { GamePhase } from '@/types/game'
import { PHASE_LABELS } from '@/types/game'

const props = defineProps<{
  phase: GamePhase
  day: number
}>()

const phaseLabel = computed(() => PHASE_LABELS[props.phase] ?? props.phase)

const phaseIcon = computed(() => {
  switch (props.phase) {
    case 'Night':
      return Moon
    case 'Day':
      return Sunny
    case 'Discussion':
      return ChatDotRound
    case 'Vote':
      return Select
    case 'GameOver':
      return Trophy
    default:
      return Sunny
  }
})

const phaseDescription = computed(() => {
  switch (props.phase) {
    case 'Night':
      return '狼人请睁眼，女巫请使用药水，预言家请查验'
    case 'Day':
      return '天亮了，请大家开始发言'
    case 'Discussion':
      return '请依次发言，讨论局势'
    case 'Vote':
      return '请投票选择一名玩家'
    case 'GameOver':
      return '游戏已结束'
    default:
      return ''
  }
})
</script>

<style scoped>
.phase-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  border-radius: 12px;
  margin-bottom: 20px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.phase-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}

.phase-info {
  flex: 1;
}

.phase-title {
  font-size: 20px;
  font-weight: 700;
  color: #e0e0e0;
  margin: 0 0 4px;
}

.phase-subtitle {
  font-size: 13px;
  color: #999;
  margin: 0;
}

.phase-day {
  display: flex;
  align-items: center;
}

/* 不同阶段的颜色主题 */
.phase-night .phase-icon {
  color: #9b59b6;
}

.phase-day .phase-icon {
  color: #f39c12;
}

.phase-discussion .phase-icon {
  color: #3498db;
}

.phase-vote .phase-icon {
  color: #e67e22;
}

.phase-gameover .phase-icon {
  color: #95a5a6;
}
</style>
