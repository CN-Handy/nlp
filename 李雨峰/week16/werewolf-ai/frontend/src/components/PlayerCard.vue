<template>
  <el-card :class="['player-card', { 'is-dead': !player.isAlive, 'is-current': isCurrentPlayer }]">
    <div class="card-content">
      <div class="avatar-section">
        <el-avatar :size="56" :style="avatarStyle">
          {{ player.name.charAt(0).toUpperCase() }}
        </el-avatar>
        <el-tag v-if="!player.isAlive" type="danger" size="small" class="dead-tag">已淘汰</el-tag>
        <el-tag v-else-if="player.isHuman" type="success" size="small" class="human-tag">人类</el-tag>
        <el-tag v-else type="info" size="small" class="ai-tag">AI</el-tag>
      </div>
      <div class="info-section">
        <div class="player-name">{{ player.name }}</div>
        <div v-if="showRole" class="player-role">
          <el-tag :type="roleTagType" size="small">
            {{ roleLabel }}
          </el-tag>
        </div>
        <div v-else class="player-role hidden">角色隐藏</div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Player, PlayerRole } from '@/types/game'
import { ROLE_LABELS } from '@/types/game'

const props = withDefaults(
  defineProps<{
    player: Player
    showRole?: boolean
    isCurrentPlayer?: boolean
  }>(),
  {
    showRole: false,
    isCurrentPlayer: false,
  },
)

const roleLabel = computed(() => {
  if (!props.player.role) return '未知'
  return ROLE_LABELS[props.player.role as PlayerRole] ?? '未知'
})

const roleTagType = computed(() => {
  switch (props.player.role) {
    case 'Werewolf':
      return 'danger'
    case 'Villager':
      return 'success'
    case 'Seer':
      return 'warning'
    case 'Witch':
      return ''
    case 'Hunter':
      return 'info'
    case 'Idiot':
      return 'info'
    default:
      return ''
  }
})

const avatarStyle = computed(() => {
  const colors: Record<string, string> = {
    Werewolf: 'background: linear-gradient(135deg, #e74c3c, #c0392b)',
    Villager: 'background: linear-gradient(135deg, #27ae60, #2ecc71)',
    Seer: 'background: linear-gradient(135deg, #f39c12, #e67e22)',
    Witch: 'background: linear-gradient(135deg, #9b59b6, #8e44ad)',
    Hunter: 'background: linear-gradient(135deg, #3498db, #2980b9)',
    Idiot: 'background: linear-gradient(135deg, #1abc9c, #16a085)',
  }
  return props.player.role ? colors[props.player.role] : 'background: linear-gradient(135deg, #95a5a6, #7f8c8d)'
})
</script>

<style scoped>
.player-card {
  transition: all 0.3s ease;
  border-radius: 12px;
}

.player-card.is-dead {
  opacity: 0.5;
  filter: grayscale(80%);
}

.player-card.is-current {
  box-shadow: 0 0 0 2px #409eff;
}

.card-content {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px;
}

.avatar-section {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.dead-tag,
.human-tag,
.ai-tag {
  margin-top: 4px;
}

.info-section {
  flex: 1;
  min-width: 0;
}

.player-name {
  font-size: 15px;
  font-weight: 600;
  color: #e0e0e0;
  margin-bottom: 6px;
}

.player-role {
  display: flex;
  align-items: center;
}

.player-role.hidden {
  color: #666;
  font-size: 12px;
  font-style: italic;
}

:deep(.el-card__body) {
  padding: 12px;
}
</style>
