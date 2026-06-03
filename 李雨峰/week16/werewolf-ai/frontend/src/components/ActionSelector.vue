<template>
  <el-card class="action-selector">
    <template #header>
      <div class="action-header">
        <span>{{ actionLabel }}</span>
        <el-tag v-if="currentRole" size="small" type="warning">
          {{ roleLabel }}
        </el-tag>
      </div>
    </template>

    <div class="action-description">
      {{ actionDescription }}
    </div>

    <!-- 目标选择 -->
    <div v-if="requiresTarget" class="target-selection">
      <div class="target-label">选择目标:</div>
      <div class="target-options">
        <div
          v-for="player in targetPlayers"
          :key="player.id"
          :class="['target-option', { selected: selectedTarget === player.id }]"
          @click="handleSelectTarget(player.id)"
        >
          <el-avatar :size="32">
            {{ player.name.charAt(0).toUpperCase() }}
          </el-avatar>
          <span class="target-name">{{ player.name }}</span>
          <span class="target-tag">{{ player.isHuman ? '人类' : 'AI' }}</span>
        </div>
      </div>
    </div>

    <!-- 特殊操作按钮（女巫） -->
    <div v-if="isWitch" class="witch-actions">
      <el-radio-group v-model="witchAction" class="witch-radio">
        <el-radio value="save">解药 - 拯救今夜死者</el-radio>
        <el-radio value="poison">毒药 - 毒死一名玩家</el-radio>
        <el-radio value="skip">跳过 - 不使用药水</el-radio>
      </el-radio-group>
    </div>

    <div class="action-buttons">
      <el-button
        type="primary"
        size="large"
        :disabled="!canSubmit"
        :loading="loading"
        @click="handleSubmit"
      >
        确认操作
      </el-button>
      <el-button size="large" :disabled="loading" @click="handleSkip">
        跳过
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Player, NightAction, PlayerRole } from '@/types/game'
import { ROLE_LABELS } from '@/types/game'

const props = defineProps<{
  actions: NightAction[]
  targets: Player[]
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: [action: { role: string; targetId?: string }]
  skip: []
}>()

const selectedTarget = ref<string | null>(null)
const witchAction = ref<string>('skip')

// 当前操作的角色（简化：取第一个）
const currentAction = computed(() => props.actions[0] ?? null)
const currentRole = computed(() => currentAction.value?.role ?? null)
const actionLabel = computed(() => currentAction.value?.label ?? '夜晚操作')
const actionDescription = computed(() => currentAction.value?.description ?? '请选择你的操作')
const requiresTarget = computed(() => currentAction.value?.canTarget ?? false)
const isWitch = computed(() => currentRole.value === 'Witch')

const roleLabel = computed(() => {
  if (!currentRole.value) return ''
  return ROLE_LABELS[currentRole.value as PlayerRole] ?? currentRole.value
})

const targetPlayers = computed(() => {
  // 女巫解药不需要目标，毒药需要
  if (isWitch.value && witchAction.value === 'save') {
    return []
  }
  return props.targets
})

const canSubmit = computed(() => {
  if (isWitch.value) {
    if (witchAction.value === 'skip') return true
    if (witchAction.value === 'save') return true
    // 毒药需要选择目标
    return witchAction.value === 'poison' && selectedTarget.value !== null
  }
  if (requiresTarget.value) {
    return selectedTarget.value !== null
  }
  return true
})

function handleSelectTarget(playerId: string) {
  selectedTarget.value = playerId
}

function handleSubmit() {
  if (!canSubmit.value) return

  if (isWitch.value) {
    if (witchAction.value === 'skip') {
      emit('submit', { role: currentRole.value ?? 'Witch' })
    } else if (witchAction.value === 'save') {
      emit('submit', { role: currentRole.value ?? 'Witch', targetId: 'save' })
    } else if (witchAction.value === 'poison') {
      emit('submit', { role: currentRole.value ?? 'Witch', targetId: selectedTarget.value ?? undefined })
    }
    return
  }

  emit('submit', {
    role: currentRole.value ?? '',
    targetId: selectedTarget.value ?? undefined,
  })
}

function handleSkip() {
  emit('skip')
}
</script>

<style scoped>
.action-selector {
  border-radius: 12px;
}

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-description {
  text-align: center;
  color: #ccc;
  margin-bottom: 16px;
  font-size: 14px;
}

.target-selection {
  margin-bottom: 20px;
}

.target-label {
  font-size: 14px;
  color: #999;
  margin-bottom: 10px;
}

.target-options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
  max-height: 200px;
  overflow-y: auto;
}

.target-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.target-option:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.3);
}

.target-option.selected {
  background: rgba(64, 158, 255, 0.15);
  border-color: #409eff;
}

.target-name {
  flex: 1;
  font-size: 13px;
  color: #e0e0e0;
}

.target-tag {
  font-size: 11px;
  color: #888;
}

.witch-actions {
  margin-bottom: 20px;
}

.witch-radio {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

:deep(.el-radio__label) {
  color: #e0e0e0 !important;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
