<template>
  <el-card class="chat-box">
    <template #header>
      <div class="chat-header">
        <span>发言记录</span>
        <el-tag size="small" type="info">{{ events.length }} 条</el-tag>
      </div>
    </template>
    <div ref="scrollContainer" class="chat-messages">
      <div v-if="events.length === 0" class="empty-chat">暂无发言</div>
      <div
        v-for="event in displayEvents"
        :key="event.id"
        :class="['chat-message', `type-${event.type}`]"
      >
        <div class="message-meta">
          <span class="message-phase">{{ phaseLabel(event.phase) }}</span>
          <span class="message-time">{{ formatTime(event.timestamp) }}</span>
        </div>
        <div class="message-content">
          <span v-if="event.actorId" class="message-actor">
            [{{ actorName(event.actorId) }}]
          </span>
          <span class="message-text">{{ event.content }}</span>
        </div>
      </div>
    </div>
    <div v-if="showInput" class="chat-input">
      <el-input
        v-model="inputText"
        placeholder="输入发言内容..."
        :disabled="loading"
        @keyup.enter="handleSend"
      >
        <template #append>
          <el-button type="primary" :loading="loading" @click="handleSend">
            发送
          </el-button>
        </template>
      </el-input>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import type { GameEvent, GamePhase } from '@/types/game'
import { PHASE_LABELS } from '@/types/game'

const props = withDefaults(
  defineProps<{
    events: GameEvent[]
    showInput?: boolean
    loading?: boolean
    actors?: Map<string, string>
  }>(),
  {
    showInput: false,
    loading: false,
    actors: () => new Map(),
  },
)

const emit = defineEmits<{
  send: [content: string]
}>()

const inputText = ref('')
const scrollContainer = ref<HTMLElement | null>(null)

// 最多显示 100 条
const displayEvents = computed(() => props.events.slice(-100))

function phaseLabel(phase: GamePhase): string {
  return PHASE_LABELS[phase] ?? phase
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function actorName(actorId: string): string {
  return props.actors.get(actorId) ?? actorId.slice(0, 6)
}

async function handleSend() {
  const content = inputText.value.trim()
  if (!content || props.loading) return
  emit('send', content)
  inputText.value = ''
}

// 自动滚动到底部
watch(
  displayEvents,
  async () => {
    await nextTick()
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  },
  { deep: true },
)
</script>

<style scoped>
.chat-box {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  min-height: 200px;
  max-height: 500px;
}

.empty-chat {
  text-align: center;
  color: #888;
  padding: 40px 0;
  font-size: 14px;
}

.chat-message {
  padding: 8px 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-left: 3px solid rgba(64, 158, 255, 0.5);
}

.chat-message.type-death {
  border-left-color: #f56c6c;
  background: rgba(245, 108, 108, 0.08);
}

.chat-message.type-vote_result {
  border-left-color: #e6a23c;
  background: rgba(230, 162, 60, 0.08);
}

.message-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #888;
  margin-bottom: 4px;
}

.message-phase {
  color: #409eff;
}

.message-content {
  font-size: 14px;
  line-height: 1.5;
}

.message-actor {
  color: #409eff;
  font-weight: 600;
  margin-right: 6px;
}

.message-text {
  color: #e0e0e0;
}

.chat-input {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
