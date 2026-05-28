<template>
  <div class="setup-container">
    <div class="setup-card">
      <h2 class="setup-title">创建新游戏</h2>

      <!-- Game Mode Tabs -->
      <div class="mode-tabs">
        <button
          class="mode-tab"
          :class="{ active: gameMode === 'single' }"
          @click="gameMode = 'single'"
        >
          🎮 单局对战
        </button>
        <button
          class="mode-tab"
          :class="{ active: gameMode === 'tournament' }"
          @click="gameMode = 'tournament'"
        >
          🏆 锦标赛（自进化）
        </button>
      </div>

      <div class="form-group">
        <label class="form-label">游戏配置</label>
        <select v-model="selectedConfig" class="form-select">
          <option
            v-for="(cfg, key) in configs"
            :key="key"
            :value="key"
          >
            {{ cfg.name }}（{{ cfg.player_count }}人）— {{ cfg.description }}
          </option>
        </select>
        <p class="form-hint" v-if="selectedConfig && configs[selectedConfig]">
          玩家数量：{{ configs[selectedConfig].player_count }} 人
        </p>
      </div>

      <div class="form-group" v-if="gameMode === 'tournament'">
        <label class="form-label">对局数量</label>
        <select v-model.number="numGames" class="form-select">
          <option :value="3">3 局（快速测试）</option>
          <option :value="5">5 局（标准）</option>
          <option :value="10">10 局（深度）</option>
          <option :value="20">20 局（全面）</option>
        </select>
      </div>

      <div class="form-group" v-if="gameMode === 'tournament'">
        <label class="form-label checkbox-label">
          <input type="checkbox" v-model="enableEvolution" />
          <span>启用跨局经验进化</span>
        </label>
        <p class="form-hint">Agent会在每局后学习经验，持续优化策略</p>
      </div>

      <div class="form-group">
        <label class="form-label checkbox-label">
          <input type="checkbox" v-model="shuffle" />
          <span>打乱角色分配</span>
        </label>
      </div>

      <button
        class="primary create-btn"
        :disabled="loading"
        @click="handleCreate"
      >
        {{ loading ? '创建中...' : (gameMode === 'tournament' ? '🏆 开始锦标赛' : '🎮 开始游戏') }}
      </button>

      <!-- Tournament Progress -->
      <div v-if="tournamentRunning" class="tournament-progress">
        <div class="progress-bar-wrap">
          <div class="progress-bar-fill" :style="{ width: tournamentProgress + '%' }"></div>
        </div>
        <p class="progress-text">{{ tournamentText }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  configs: { type: Object, required: true },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['create', 'start-tournament'])

const selectedConfig = ref('standard_6')
const shuffle = ref(true)
const gameMode = ref('single')
const numGames = ref(5)
const enableEvolution = ref(true)
const tournamentRunning = ref(false)
const tournamentProgress = ref(0)
const tournamentText = ref('')

async function handleCreate() {
  if (gameMode.value === 'tournament') {
    await startTournament()
  } else {
    emit('create', selectedConfig.value, shuffle.value)
  }
}

async function startTournament() {
  tournamentRunning.value = true
  tournamentProgress.value = 0
  tournamentText.value = '正在启动锦标赛...'

  try {
    const res = await fetch('/tournament', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        config_name: selectedConfig.value,
        num_games: numGames.value,
        enable_evolution: enableEvolution.value,
      }),
    })
    if (!res.ok) throw new Error('Tournament failed')
    const result = await res.json()
    tournamentProgress.value = 100
    tournamentText.value = `锦标赛完成！共 ${result.total_games} 局，好人胜率 ${(result.good_win_rate * 100).toFixed(0)}%`

    // 保存结果并跳转到排行榜
    alert(
      `锦标赛完成！\n` +
      `总局数: ${result.total_games}\n` +
      `好人胜率: ${(result.good_win_rate * 100).toFixed(0)}%\n` +
      `平均回合: ${result.avg_rounds}\n` +
      `进化提升: ${result.evolution_trend?.improvement || 0} 分`
    )
  } catch (e) {
    tournamentText.value = '锦标赛启动失败: ' + e.message
  } finally {
    tournamentRunning.value = false
  }
}
</script>

<style scoped>
.setup-container {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 60px;
}

.setup-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 36px;
  width: 100%;
  max-width: 520px;
}

.setup-title {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 28px;
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--text-primary);
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-green);
}

.form-select {
  width: 100%;
}

.form-hint {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 6px;
}

.create-btn {
  width: 100%;
  padding: 12px;
  font-size: 16px;
  font-weight: 600;
  margin-top: 8px;
}
</style>
