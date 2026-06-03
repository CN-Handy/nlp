<template>
  <div class="spectate-view">
    <div class="spectate-container">
      <!-- 顶部信息栏 -->
      <div class="top-bar">
        <el-button text @click="handleBack">
          <el-icon><Back /></el-icon>
          返回首页
        </el-button>
        <div class="top-bar-center">
          <el-tag size="large" effect="dark" class="phase-tag">
            {{ phaseLabel }}
          </el-tag>
          <el-tag size="small" :type="connected ? 'success' : 'danger'">
            {{ connected ? '实时连接' : '已断开' }}
          </el-tag>
          <el-tag v-if="players.length > 0" size="small" type="info">
            存活 {{ aliveCount }} / 共 {{ players.length }}
          </el-tag>
        </div>
        <div class="top-bar-right">
          <span class="day-label">第 {{ currentDay }} 天</span>
        </div>
      </div>

      <!-- 玩家区域 -->
      <div class="players-section">
        <div class="section-title">
          玩家状态
          <span v-if="players.length === 0" class="players-loading">（等待游戏开始...）</span>
        </div>
        <div v-if="players.length === 0" class="players-placeholder">
          <el-empty description="等待玩家加入..." :image-size="80" />
        </div>
        <div v-else class="players-grid">
          <div
            v-for="player in players"
            :key="player.id"
            class="player-card"
            :class="{ 'is-dead': !player.isAlive, 'is-werewolf': showRoles && player.role === 'Werewolf' }"
          >
            <div class="player-avatar">
              <el-icon :size="28">
                <User v-if="player.isAlive" />
                <Remove v-else />
              </el-icon>
            </div>
            <div class="player-name" :title="player.name">{{ player.name }}</div>
            <div v-if="player.role" class="player-role">
              <el-tag :type="getRoleTagType(player.role)" size="small" effect="dark">
                {{ roleLabel(player.role) }}
              </el-tag>
            </div>
            <div v-else-if="!player.isAlive" class="player-status dead-label">已淘汰</div>
            <div v-else class="player-status alive-label">存活</div>
          </div>
        </div>
      </div>

      <!-- 事件流区域 -->
      <div class="event-section">
        <div class="section-title">
          事件记录
          <el-badge :value="events.length" type="primary" class="event-badge" />
        </div>
        <div class="event-list" ref="eventListRef">
          <div
            v-for="(event, index) in events"
            :key="index"
            class="event-item"
            :class="'event-' + event.event_type"
          >
            <div class="event-header">
              <span class="event-time">{{ formatTime(event.timestamp) }}</span>
              <span class="event-type-label">{{ eventTypeLabel(event.event_type) }}</span>
              <span class="event-actor" v-if="event.actor_name">{{ event.actor_name }}</span>
              <span class="event-arrow" v-if="event.target_name">→</span>
              <span class="event-target" v-if="event.target_name">{{ event.target_name }}</span>
            </div>
            <div class="event-content">{{ eventContent(event) }}</div>
          </div>
          <div v-if="events.length === 0" class="event-empty">
            <el-empty description="等待游戏事件..." />
          </div>
        </div>
      </div>

      <!-- 游戏结束 -->
      <el-dialog v-model="gameOverDialog" title="游戏结束" width="480px" :show-close="false">
        <el-result
          :icon="winner === 'villagers' ? 'success' : 'warning'"
          :title="winner === 'villagers' ? '好人阵营胜利' : '狼人阵营胜利'"
          :sub-title="winnerMessage"
        >
          <template #extra>
            <el-button type="primary" @click="handleBack">返回首页</el-button>
          </template>
        </el-result>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Back, User, Remove } from '@element-plus/icons-vue'
import { wsService } from '@/api/ws'

defineProps<{
  roomId: string
}>()

const router = useRouter()
const route = useRoute()
const roomId = computed(() => route.params.roomId as string)

// 状态
const connected = ref(false)
const currentDay = ref(1)
const currentPhase = ref('WAITING')
const events = ref<any[]>([])
const players = ref<PlayerInfo[]>([])
const showRoles = ref(false)
const gameOverDialog = ref(false)
const winner = ref('')
const eventListRef = ref<HTMLElement | null>(null)

interface PlayerInfo {
  id: string
  name: string
  role: string | null
  isAlive: boolean
}

// 计算属性
const aliveCount = computed(() => players.value.filter((p) => p.isAlive).length)

const phaseLabel = computed(() => {
  const labels: Record<string, string> = {
    WAITING: '等待中',
    NIGHT_START: '夜晚降临',
    WEREWOLF_TURN: '狼人行动中',
    SEER_TURN: '预言家查验中',
    WITCH_TURN: '女巫行动中',
    NIGHT_END: '夜晚结束',
    DAY_START: '天亮',
    DEATH_ANNOUNCE: '公布死亡信息',
    DISCUSSION: '讨论阶段',
    VOTING: '投票阶段',
    VOTE_RESULT: '投票结果',
    GAME_OVER: '游戏结束',
  }
  return labels[currentPhase.value] || currentPhase.value
})

const winnerMessage = computed(() => {
  const deadPlayers = players.value.filter((p) => !p.isAlive)
  const alivePlayers = players.value.filter((p) => p.isAlive)
  return `存活 ${alivePlayers.length} 人，淘汰 ${deadPlayers.length} 人`
})

// 工具函数
function roleLabel(role: string | null): string {
  const labels: Record<string, string> = {
    Werewolf: '狼人',
    Villager: '村民',
    Seer: '预言家',
    Witch: '女巫',
    Hunter: '猎人',
    Idiot: '白痴',
  }
  return role ? labels[role] || role : '未知'
}

function getRoleTagType(role: string): string {
  const typeMap: Record<string, string> = {
    Werewolf: 'danger',
    Villager: 'info',
    Seer: 'warning',
    Witch: 'success',
    Hunter: 'danger',
    Idiot: 'info',
  }
  return typeMap[role] || 'info'
}

function eventTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    game_start: '🎮 游戏开始',
    phase_change: '🔄 阶段变更',
    night_action: '🌙 夜晚行动',
    death: '💀 死亡',
    speak: '🗣️ 发言',
    vote: '🗳️ 投票',
    vote_result: '📊 投票结果',
    witch_poison: '☠️ 女巫用毒',
    witch_heal: '💊 女巫救人',
    seer_inspect: '🔍 预言家查验',
    game_over: '🏆 游戏结束',
  }
  return labels[type] || type
}

function formatTime(timestamp: string): string {
  if (!timestamp) return ''
  try {
    const d = new Date(timestamp)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

function eventContent(event: any): string {
  const { event_type, data, actor_name, actor_role, target_name, target_role } = event

  switch (event_type) {
    case 'game_start':
      return `游戏开始！共 ${data?.player_count || players.value.length} 名玩家参与对局`

    case 'phase_change':
      return `阶段变更：${phaseName(data?.from_phase)} → ${phaseName(data?.to_phase)}`

    case 'death': {
      const killedBy = data?.killed_by === 'werewolf' ? '狼人' : data?.killed_by === 'witch_poison' ? '女巫（毒药）' : data?.killed_by || '未知原因'
      const roleName = target_role ? roleLabel(target_role) : '未知身份'
      return `${target_name || '某玩家'}（${roleName}）被淘汰，死因：${killedBy}`
    }

    case 'witch_poison':
      return `${target_name || '某玩家'} 被女巫毒杀`

    case 'witch_heal':
      return `女巫救活了 ${target_name || '某玩家'}`

    case 'seer_inspect':
      return `预言家查验了 ${target_name || '某玩家'}，结果是：${data?.is_werewolf ? '🐺 狼人' : '👤 好人'}`

    case 'vote_result': {
      const votes = data?.votes_received as Record<string, number> | undefined
      const voteSummary = votes
        ? Object.entries(votes)
            .map(([id, count]) => {
              const name = id === data?.eliminated_id ? target_name || id : `玩家(${id.slice(0, 6)})`
              return `${name}(${count}票)`
            })
            .join('，')
        : ''
      if (data?.eliminated_id) {
        const roleName = target_role ? roleLabel(target_role) : ''
        return `投票结果：${target_name || '某玩家'}（${roleName}）被淘汰。得票：${voteSummary}`
      }
      return `投票结果：无人被淘汰（平票或弃权）。得票：${voteSummary}`
    }

    case 'game_over':
      return `游戏结束！获胜方：${data?.winner === 'villagers' ? '好人阵营 🎉' : '狼人阵营 🐺'}`

    case 'speak': {
      const text = data?.text || ''
      const roleName = actor_role ? roleLabel(actor_role) : ''
      return `${actor_name || '某玩家'}（${roleName}）：${text}`
    }

    default:
      return JSON.stringify(data || '')
  }
}

function phaseName(phase: string | undefined): string {
  if (!phase) return ''
  const labels: Record<string, string> = {
    waiting: '等待中',
    night_start: '夜晚降临',
    werewolf_turn: '狼人行动',
    seer_turn: '预言家查验',
    witch_turn: '女巫行动',
    night_end: '夜晚结束',
    day_start: '天亮',
    death_announce: '死亡公布',
    discussion: '讨论',
    voting: '投票',
    vote_result: '投票结果',
    game_over: '游戏结束',
  }
  return labels[phase] || phase
}

function handleBack() {
  wsService.disconnect()
  router.push({ name: 'home' })
}

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (eventListRef.value) {
      eventListRef.value.scrollTop = eventListRef.value.scrollHeight
    }
  })
}

/** 更新或添加玩家信息 */
function upsertPlayer(id: string, updates: Partial<PlayerInfo>) {
  const idx = players.value.findIndex((p) => p.id === id)
  if (idx >= 0) {
    players.value[idx] = { ...players.value[idx], ...updates }
  } else {
    players.value.push({
      id,
      name: updates.name || `玩家_${id.slice(0, 6)}`,
      role: updates.role ?? null,
      isAlive: updates.isAlive ?? true,
    })
  }
}

// WebSocket 事件处理
function handleWsMessage(payload: any) {
  if (!payload || !payload.event_type) return

  const event = payload as any
  events.value.push(event)

  // 从 game_start 事件构建玩家列表
  if (event.event_type === 'game_start') {
    const pData = event.data?.players
    if (pData && Array.isArray(pData)) {
      players.value = pData.map((p: any) => ({
        id: p.id,
        name: p.name || `玩家_${p.id.slice(0, 6)}`,
        role: p.role ?? null,
        isAlive: p.is_alive !== undefined ? p.is_alive : true,
      }))
    }
  }

  // 从 death 事件更新玩家存活状态并揭示身份
  if (event.event_type === 'death') {
    const tid = event.target_id
    if (tid) {
      upsertPlayer(tid, {
        name: event.target_name,
        isAlive: false,
        role: event.target_role,
      })
    }
  }

  // 从 vote_result 更新被淘汰玩家
  if (event.event_type === 'vote_result' && event.data?.eliminated_id) {
    const tid = event.data.eliminated_id
    upsertPlayer(tid, {
      name: event.target_name,
      isAlive: false,
      role: event.target_role,
    })
  }

  // 游戏结束时揭示所有身份
  if (event.event_type === 'game_over') {
    winner.value = event.data?.winner || ''
    showRoles.value = true
    if (event.data?.all_roles) {
      for (const ri of event.data.all_roles) {
        upsertPlayer(ri.id, {
          name: ri.name,
          role: ri.role,
          isAlive: ri.is_alive,
        })
      }
    }
    setTimeout(() => {
      gameOverDialog.value = true
    }, 500)
  }

  // 更新阶段
  if (event.phase) {
    currentPhase.value = event.phase
  }
  if (event.day_number) {
    currentDay.value = event.day_number
  }

  scrollToBottom()
}

// 初始化玩家列表
function initPlayersFromStart(_payload: unknown) {
  // Spectator connected, waiting for game events
}

onMounted(() => {
  const wsUrl = `/api/v1/games/spectate/${roomId.value}`
  wsService.connect(wsUrl)

  wsService.on('spectate_start', initPlayersFromStart)
  wsService.on('game_event', handleWsMessage)

  wsService.on('open', () => {
    connected.value = true
  })

  wsService.on('close', () => {
    connected.value = false
  })
})

onUnmounted(() => {
  wsService.disconnect()
})
</script>

<style scoped>
.spectate-view {
  min-height: 100vh;
  background: #0d1117;
  color: #c9d1d9;
  padding: 16px;
}

.spectate-container {
  max-width: 1200px;
  margin: 0 auto;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 8px;
}

.top-bar-center {
  display: flex;
  align-items: center;
  gap: 12px;
}

.phase-tag {
  font-size: 14px;
  font-weight: 600;
}

.day-label {
  font-size: 14px;
  color: #8b949e;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #58a6ff;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.players-loading {
  font-size: 13px;
  color: #8b949e;
  font-weight: 400;
}

.players-placeholder {
  padding: 20px 0;
}

.players-section {
  margin-bottom: 24px;
}

.players-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
}

.player-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  transition: all 0.2s;
}

.player-card.is-dead {
  opacity: 0.4;
  border-color: rgba(255, 0, 0, 0.3);
}

.player-card.is-werewolf {
  border-color: rgba(255, 100, 100, 0.4);
}

.player-avatar {
  width: 40px;
  height: 40px;
  margin: 0 auto 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
}

.player-name {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.player-role {
  margin-bottom: 4px;
}

.player-status {
  font-size: 11px;
  color: #8b949e;
}

.alive-label {
  color: #3fb950;
}

.dead-label {
  color: #f85149;
}

.event-section {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 16px;
}

.event-list {
  max-height: 60vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.event-item {
  background: rgba(255, 255, 255, 0.05);
  border-left: 3px solid #58a6ff;
  border-radius: 4px;
  padding: 10px 12px;
  animation: fadeIn 0.3s ease;
}

.event-item.event-speak {
  border-left-color: #3fb950;
  background: rgba(63, 185, 80, 0.05);
}

.event-item.event-death {
  border-left-color: #f85149;
}

.event-item.event-witch_poison {
  border-left-color: #f85149;
}

.event-item.event-witch_heal {
  border-left-color: #3fb950;
}

.event-item.event-seer_inspect {
  border-left-color: #d2a8ff;
}

.event-item.event-game_over {
  border-left-color: #f0883e;
  background: rgba(240, 136, 62, 0.1);
}

.event-item.event-phase_change {
  border-left-color: #a371f7;
}

.event-item.event-vote_result {
  border-left-color: #58a6ff;
}

.event-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.event-time {
  font-size: 11px;
  color: #8b949e;
  font-family: monospace;
}

.event-type-label {
  font-size: 12px;
  font-weight: 600;
  color: #58a6ff;
}

.event-actor {
  font-size: 13px;
  color: #c9d1d9;
  font-weight: 500;
}

.event-arrow {
  color: #8b949e;
}

.event-target {
  font-size: 13px;
  color: #f0883e;
  font-weight: 500;
}

.event-content {
  font-size: 13px;
  color: #c9d1d9;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.event-empty {
  padding: 40px 0;
}

.event-badge {
  margin-left: 8px;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .players-grid {
    grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  }
}
</style>
