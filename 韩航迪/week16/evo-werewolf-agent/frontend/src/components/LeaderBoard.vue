<template>
  <div class="leaderboard-container">
    <div class="lb-header">
      <h2 class="lb-title">🏆 Agent 排行榜</h2>
      <div class="lb-filters">
        <select v-model="selectedRole" @change="fetchData">
          <option value="">全部角色</option>
          <option value="werewolf">🐺 狼人</option>
          <option value="seer">🔮 预言家</option>
          <option value="witch">🧪 女巫</option>
          <option value="hunter">🏹 猎人</option>
          <option value="villager">👤 村民</option>
        </select>
        <select v-model="sortBy" @change="fetchData">
          <option value="composite_score">综合排名</option>
          <option value="win_rate">胜率</option>
          <option value="avg_overall_score">平均评分</option>
          <option value="avg_vote_accuracy">投票准确率</option>
          <option value="games_played">对局数</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="lb-loading">加载中...</div>

    <div v-else-if="rankings.length === 0" class="lb-empty">
      暂无数据，请先完成一局游戏。
    </div>

    <div v-else class="lb-content">
      <!-- Rankings Table -->
      <div class="lb-table-wrap">
        <table class="lb-table">
          <thead>
            <tr>
              <th class="col-rank">#</th>
              <th class="col-name">角色</th>
              <th class="col-games">对局数</th>
              <th class="col-win">胜率</th>
              <th class="col-score">综合评分</th>
              <th class="col-vote">投票准确率</th>
              <th class="col-survival">存活率</th>
              <th class="col-mvp">MVP</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(entry, idx) in rankings"
              :key="idx"
              class="lb-row"
              :class="{ 'top-3': idx < 3 }"
            >
              <td class="col-rank">
                <span class="rank-badge" :class="'rank-' + (idx + 1)">
                  {{ idx + 1 }}
                </span>
              </td>
              <td class="col-name">
                <div class="name-cell">
                  <span class="role-icon">{{ roleIcon(entry.role_type) }}</span>
                  <span>{{ entry.player_name || entry.role_type }}</span>
                  <span class="style-tag">{{ entry.decision_style }}</span>
                </div>
              </td>
              <td class="col-games">{{ entry.games_played }}</td>
              <td class="col-win">
                <div class="win-bar-container">
                  <div class="win-bar" :style="{ width: (entry.win_rate * 100) + '%' }"></div>
                  <span class="win-text">{{ (entry.win_rate * 100).toFixed(0) }}%</span>
                </div>
              </td>
              <td class="col-score">{{ entry.composite_score?.toFixed(1) || entry.avg_overall_score?.toFixed(1) }}</td>
              <td class="col-vote">{{ (entry.avg_vote_accuracy * 100).toFixed(1) }}%</td>
              <td class="col-survival">{{ entry.avg_survival?.toFixed(1) || '—' }}%</td>
              <td class="col-mvp">{{ entry.mvp_count || 0 }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Role Comparison -->
      <div v-if="roleComparison && Object.keys(roleComparison).length > 0" class="lb-comparison">
        <h3 class="comparison-title">📊 各角色平均表现对比</h3>
        <div class="comparison-grid">
          <div
            v-for="(data, role) in roleComparison"
            :key="role"
            class="comparison-card"
          >
            <div class="comp-role">{{ roleIcon(role) }} {{ roleName(role) }}</div>
            <div class="comp-stat">
              <span class="comp-label">平均胜率</span>
              <span class="comp-value">{{ (data.avg_win_rate * 100).toFixed(1) }}%</span>
            </div>
            <div class="comp-stat">
              <span class="comp-label">平均评分</span>
              <span class="comp-value">{{ data.avg_score?.toFixed(1) }}</span>
            </div>
            <div class="comp-stat">
              <span class="comp-label">总对局</span>
              <span class="comp-value">{{ data.total_games }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="lb-actions">
      <button @click="fetchData">🔄 刷新数据</button>
      <button class="primary" @click="$emit('back')">🏠 返回大厅</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const rankings = ref([])
const roleComparison = ref({})
const selectedRole = ref('')
const sortBy = ref('composite_score')
const loading = ref(false)

defineEmits(['back'])

const roleIcons = {
  werewolf: '🐺',
  seer: '🔮',
  witch: '🧪',
  hunter: '🏹',
  villager: '👤',
}

const roleNames = {
  werewolf: '狼人',
  seer: '预言家',
  witch: '女巫',
  hunter: '猎人',
  villager: '村民',
}

function roleIcon(role) {
  return roleIcons[role] || '❓'
}

function roleName(role) {
  return roleNames[role] || role
}

async function fetchData() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (selectedRole.value) params.set('role_type', selectedRole.value)
    params.set('sort_by', sortBy.value)
    params.set('limit', '20')

    const res = await fetch(`/leaderboard?${params}`)
    if (res.ok) {
      const data = await res.json()
      rankings.value = data.rankings || []
      roleComparison.value = data.role_comparison || {}
    }
  } catch (e) {
    console.error('获取排行榜失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.leaderboard-container {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 0;
}

.lb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}

.lb-title {
  font-size: 22px;
  font-weight: 700;
}

.lb-filters {
  display: flex;
  gap: 8px;
}

.lb-loading, .lb-empty {
  text-align: center;
  padding: 60px 0;
  color: var(--text-muted);
  font-size: 14px;
}

/* Table */
.lb-table-wrap {
  overflow-x: auto;
  margin-bottom: 32px;
}

.lb-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.lb-table th {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid var(--border-color);
  color: var(--text-muted);
  font-size: 12px;
  text-transform: uppercase;
  font-weight: 600;
  white-space: nowrap;
}

.lb-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
}

.lb-row:hover {
  background: var(--bg-hover);
}

.lb-row.top-3 {
  background: rgba(210, 153, 34, 0.05);
}

.col-rank { width: 50px; }
.col-name { min-width: 140px; }
.col-games { width: 70px; text-align: center; }
.col-win { width: 140px; }
.col-score { width: 90px; text-align: center; color: var(--accent-yellow); font-weight: 600; }
.col-vote { width: 100px; text-align: center; }
.col-survival { width: 80px; text-align: center; }
.col-mvp { width: 60px; text-align: center; color: var(--accent-yellow); }

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 700;
  background: var(--bg-hover);
}

.rank-badge.rank-1 { background: #d29922; color: #000; }
.rank-badge.rank-2 { background: #8b949e; color: #000; }
.rank-badge.rank-3 { background: #8b6914; color: #fff; }

.name-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.role-icon {
  font-size: 16px;
}

.style-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--bg-hover);
  color: var(--text-muted);
}

.win-bar-container {
  position: relative;
  height: 20px;
  background: var(--bg-hover);
  border-radius: 4px;
  overflow: hidden;
}

.win-bar {
  height: 100%;
  background: linear-gradient(90deg, #238636, #3fb950);
  border-radius: 4px;
  transition: width 0.3s;
  min-width: 2px;
}

.win-text {
  position: absolute;
  top: 50%;
  left: 4px;
  transform: translateY(-50%);
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}

/* Role Comparison */
.lb-comparison {
  margin-bottom: 24px;
}

.comparison-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-secondary);
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}

.comparison-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px;
}

.comp-role {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.comp-stat {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.comp-label {
  font-size: 12px;
  color: var(--text-muted);
}

.comp-value {
  font-size: 13px;
  font-weight: 600;
}

/* Actions */
.lb-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}
</style>
