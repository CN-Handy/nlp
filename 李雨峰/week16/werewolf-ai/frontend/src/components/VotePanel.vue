<template>
  <el-card class="vote-panel">
    <template #header>
      <div class="vote-header">
        <span>投票阶段</span>
        <el-tag v-if="selectedTarget" type="primary" size="small">
          已选择: {{ selectedName }}
        </el-tag>
      </div>
    </template>

    <div class="vote-description">
      请投票选择一名玩家进行淘汰
    </div>

    <div v-if="loading" class="vote-loading">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else class="vote-options">
      <div
        v-for="player in candidates"
        :key="player.id"
        :class="['vote-option', { selected: selectedTarget === player.id }]"
        @click="handleSelect(player.id)"
      >
        <div class="player-info">
          <el-avatar :size="36" :style="getAvatarStyle(player)">
            {{ player.name.charAt(0).toUpperCase() }}
          </el-avatar>
          <div class="player-details">
            <span class="player-name">{{ player.name }}</span>
            <span class="player-tag">{{ player.isHuman ? '人类' : 'AI' }}</span>
          </div>
        </div>
        <el-icon v-if="selectedTarget === player.id" class="check-icon">
          <Check />
        </el-icon>
      </div>
    </div>

    <div class="vote-actions">
      <el-button
        type="primary"
        size="large"
        :disabled="!selectedTarget || loading"
        :loading="loading"
        @click="handleVote"
      >
        确认投票
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Check } from '@element-plus/icons-vue'
import type { Player } from '@/types/game'

const props = defineProps<{
  candidates: Player[]
  loading?: boolean
}>()

const emit = defineEmits<{
  vote: [targetId: string]
}>()

const selectedTarget = ref<string | null>(null)

const selectedName = computed(() => {
  if (!selectedTarget.value) return ''
  const player = props.candidates.find((p) => p.id === selectedTarget.value)
  return player?.name ?? ''
})

function handleSelect(playerId: string) {
  selectedTarget.value = playerId
}

async function handleVote() {
  if (!selectedTarget.value || props.loading) return
  emit('vote', selectedTarget.value)
}

function getAvatarStyle(player: Player): Record<string, string> {
  // 简化样式，可根据角色扩展
  return {
    background: player.isHuman
      ? 'linear-gradient(135deg, #409eff, #337ecc)'
      : 'linear-gradient(135deg, #909399, #73767a)',
  }
}
</script>

<style scoped>
.vote-panel {
  border-radius: 12px;
}

.vote-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.vote-description {
  text-align: center;
  color: #ccc;
  margin-bottom: 16px;
  font-size: 14px;
}

.vote-loading {
  padding: 20px 0;
}

.vote-options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
  max-height: 300px;
  overflow-y: auto;
}

.vote-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.vote-option:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.3);
}

.vote-option.selected {
  background: rgba(64, 158, 255, 0.15);
  border-color: #409eff;
}

.player-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.player-details {
  display: flex;
  flex-direction: column;
}

.player-name {
  font-size: 14px;
  font-weight: 500;
  color: #e0e0e0;
}

.player-tag {
  font-size: 11px;
  color: #888;
}

.check-icon {
  color: #409eff;
  font-size: 20px;
}

.vote-actions {
  display: flex;
  justify-content: center;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
