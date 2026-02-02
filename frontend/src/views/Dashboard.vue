<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useSessionStore } from '../stores/sessions'
import { useStatsStore } from '../stores/stats'

const sessionStore = useSessionStore()
const statsStore = useStatsStore()

const config = ref<any>(null)
const runners = ref<any[]>([])
const health = ref<any>(null)

async function fetchData() {
  try {
    const [configRes, runnersRes, healthRes] = await Promise.all([
      axios.get('/api/config'),
      axios.get('/api/runners'),
      axios.get('/api/health')
    ])
    config.value = configRes.data
    runners.value = runnersRes.data
    health.value = healthRes.data
  } catch (e) {
    console.error('Failed to fetch data:', e)
  }
}

onMounted(() => {
  sessionStore.fetchSessions()
  fetchData()
  statsStore.fetchDailyRequests(365)
})

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`
}

function formatDate(date: string): string {
  return new Date(date).toLocaleString()
}

// Heatmap computed properties
const heatmapWeeks = computed(() => {
  const weeks: { date: string; count: number; level: number }[][] = []
  const data = statsStore.heatmapData
  
  // Group by weeks (Sunday to Saturday)
  for (let i = 0; i < data.length; i += 7) {
    const week = data.slice(i, i + 7)
    weeks.push(week)
  }
  
  return weeks
})

const monthLabels = computed(() => {
  const labels: { month: string; position: number }[] = []
  let currentMonth = ''
  const totalDays = statsStore.heatmapData.length
  
  if (totalDays === 0) return labels
  
  statsStore.heatmapData.forEach((day, index) => {
    const date = new Date(day.date)
    const month = date.toLocaleDateString('en-US', { month: 'short' })
    
    if (month !== currentMonth) {
      // Calculate position as percentage of total width
      const position = (index / totalDays) * 100
      labels.push({ month, position })
      currentMonth = month
    }
  })
  
  return labels
})

const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function getContributionColor(level: number): string {
  const colors = [
    'var(--bg-secondary)',      // 0 - empty
    'var(--contrib-level-1)',   // 1 - light
    'var(--contrib-level-2)',   // 2 - medium
    'var(--contrib-level-3)',   // 3 - dark
    'var(--contrib-level-4)'    // 4 - darkest
  ]
  return colors[level] || colors[0]
}

function showTooltip(event: MouseEvent, day: { date: string; count: number }) {
  const tooltip = document.getElementById('heatmap-tooltip')
  if (tooltip) {
    tooltip.textContent = `${statsStore.formatDate(day.date)}: ${day.count} requests`
    tooltip.style.left = `${event.pageX + 10}px`
    tooltip.style.top = `${event.pageY - 30}px`
    tooltip.style.opacity = '1'
  }
}

function hideTooltip() {
  const tooltip = document.getElementById('heatmap-tooltip')
  if (tooltip) {
    tooltip.style.opacity = '0'
  }
}
</script>

<template>
  <div class="dashboard">
    <h1>Dashboard</h1>

    <!-- Activity Heatmap -->
    <div class="card heatmap-card">
      <h2>Daily Activity</h2>
      <div class="heatmap-stats">
        <span class="stat">
          <strong>{{ statsStore.totalRequests }}</strong> requests in the last year
        </span>
        <span class="stat">
          <strong>{{ statsStore.activeDays }}</strong> active days
        </span>
      </div>
      
      <div class="heatmap-container">
        <div class="heatmap">
          <!-- Weekday labels -->
          <div class="weekday-labels">
            <div v-for="day in weekdays.slice(1, 6)" :key="day" class="weekday-label">
              {{ day }}
            </div>
          </div>
          
          <!-- Month labels -->
          <div class="month-labels">
            <div 
              v-for="(label, index) in monthLabels" 
              :key="index"
              class="month-label"
              :style="{ left: `${label.position}%` }"
            >
              {{ label.month }}
            </div>
          </div>
          
          <!-- Heatmap grid -->
          <div class="heatmap-grid">
            <div 
              v-for="(week, weekIndex) in heatmapWeeks" 
              :key="weekIndex"
              class="heatmap-week"
            >
              <div
                v-for="(day, dayIndex) in week"
                :key="`${weekIndex}-${dayIndex}`"
                class="heatmap-day"
                :style="{ backgroundColor: getContributionColor(day.level) }"
                @mouseenter="showTooltip($event, day)"
                @mouseleave="hideTooltip"
              ></div>
            </div>
          </div>
          
          <!-- Legend -->
          <div class="heatmap-legend">
            <span>Less</span>
            <div class="legend-boxes">
              <div 
                v-for="level in 5" 
                :key="level - 1"
                class="legend-box"
                :style="{ backgroundColor: getContributionColor(level - 1) }"
              ></div>
            </div>
            <span>More</span>
          </div>
        </div>
      </div>
    </div>

    <div class="stats-grid">
      <div class="card stat-card">
        <div class="stat-info">
          <div class="stat-label">Sessions</div>
          <div class="stat-value">{{ sessionStore.sessions.length }}</div>
        </div>
      </div>

      <div class="card stat-card">
        <div class="stat-info">
          <div class="stat-label">Active Runners</div>
          <div class="stat-value">{{ runners.length }}</div>
        </div>
      </div>

      <div class="card stat-card">
        <div class="stat-info">
          <div class="stat-label">Total Cost</div>
          <div class="stat-value">
            {{ formatCost(sessionStore.sessions.reduce((sum, s) => sum + s.total_cost, 0)) }}
          </div>
        </div>
      </div>

      <div class="card stat-card">
        <div class="stat-info">
          <div class="stat-label">System Status</div>
          <div class="stat-value">{{ health?.status || 'Unknown' }}</div>
        </div>
      </div>
    </div>

    <div class="content-grid">
      <div class="card">
        <h2>Recent Sessions</h2>
        <div class="session-list">
          <div
            v-for="session in sessionStore.sessions.slice(0, 5)"
            :key="session.session_id"
            class="session-item"
          >
            <div class="session-info">
              <div class="session-title">
                {{ session.title || session.session_id }}
              </div>
              <div class="session-meta">
                <span class="badge" :class="session.state">{{ session.state }}</span>
                <span>{{ session.message_count }} msgs</span>
                <span>{{ formatCost(session.total_cost) }}</span>
              </div>
            </div>
            <div class="session-time">
              {{ formatDate(session.updated_at) }}
            </div>
          </div>
          <div v-if="sessionStore.sessions.length === 0" class="empty">
            No sessions yet
          </div>
        </div>
        <RouterLink to="/sessions" class="view-all">View all sessions →</RouterLink>
      </div>

      <div class="card">
        <h2>Configuration</h2>
        <div v-if="config" class="config-list">
          <div class="config-item">
            <span class="config-label">Approved Directory</span>
            <code>{{ config.approved_directory }}</code>
          </div>
          <div class="config-item">
            <span class="config-label">Workspace</span>
            <code>{{ config.workspace_path }}</code>
          </div>
          <div class="config-item">
            <span class="config-label">Timeout</span>
            <span>{{ config.claude_timeout }}s</span>
          </div>
          <div class="config-item">
            <span class="config-label">Max Turns</span>
            <span>{{ config.claude_max_turns }}</span>
          </div>
          <div class="config-item">
            <span class="config-label">Rate Limit</span>
            <span>{{ config.rate_limit_requests }} / {{ config.rate_limit_window }}s</span>
          </div>
          <div class="config-item">
            <span class="config-label">Allowed Users</span>
            <span>{{ config.allowed_users_count }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard h1 {
  margin-bottom: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-secondary);
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.stat-label {
  color: var(--text-secondary);
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 400;
  color: var(--text-primary);
}

.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

.card h2 {
  font-size: 1.125rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-primary);
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 0.75rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 4px;
}

.session-item:hover {
  background: var(--hover-bg);
  border-color: var(--border-secondary);
}

.session-title {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.session-meta {
  display: flex;
  gap: 0.75rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.session-time {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.badge.idle {
  background: var(--status-success-bg);
  color: var(--status-success);
  border: 1px solid var(--status-success);
}

.badge.processing {
  background: var(--status-warning-bg);
  color: var(--status-warning);
  border: 1px solid var(--status-warning);
}

.badge.error {
  background: var(--status-error-bg);
  color: var(--status-error);
  border: 1px solid var(--status-error);
}

.empty {
  color: var(--text-secondary);
  text-align: center;
  padding: 2rem;
}

.view-all {
  display: block;
  text-align: right;
  margin-top: 1rem;
  font-size: 0.875rem;
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-primary);
}

.config-item:last-child {
  border-bottom: none;
}

.config-label {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.config-item code {
  font-size: 0.75rem;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Heatmap Styles - Full Width */
.heatmap-card {
  margin-bottom: 2rem;
  width: 100%;
}

.heatmap-stats {
  display: flex;
  gap: 2rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.heatmap-stats .stat strong {
  color: var(--text-primary);
  font-weight: 600;
}

.heatmap-container {
  width: 100%;
  padding: 1rem 0;
}

.heatmap {
  display: flex;
  flex-direction: column;
  position: relative;
  width: 100%;
}

.weekday-labels {
  position: absolute;
  left: 0;
  top: 35px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.weekday-label {
  height: 20px;
  line-height: 20px;
}

.month-labels {
  position: relative;
  height: 30px;
  margin-left: 50px;
}

.month-label {
  position: absolute;
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.heatmap-grid {
  display: flex;
  justify-content: space-between;
  gap: 4px;
  margin-left: 50px;
  width: calc(100% - 50px);
}

.heatmap-week {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.heatmap-day {
  width: 100%;
  aspect-ratio: 1;
  min-height: 18px;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border-primary);
}

.heatmap-day:hover {
  border-color: var(--text-primary);
  transform: scale(1.15);
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1.5rem;
  margin-left: 50px;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.legend-boxes {
  display: flex;
  gap: 4px;
}

.legend-box {
  width: 18px;
  height: 18px;
  border-radius: 3px;
  border: 1px solid var(--border-primary);
}

/* Tooltip */
#heatmap-tooltip {
  position: fixed;
  background: var(--bg-secondary);
  color: var(--text-primary);
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  font-size: 0.875rem;
  white-space: nowrap;
  z-index: 1000;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s;
  border: 1px solid var(--border-secondary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

/* Contribution level colors - will be overridden by CSS variables */
:root {
  --contrib-level-1: #9be9a8;
  --contrib-level-2: #40c463;
  --contrib-level-3: #30a14e;
  --contrib-level-4: #216e39;
}

@media (prefers-color-scheme: dark) {
  :root {
    --contrib-level-1: #0e4429;
    --contrib-level-2: #006d32;
    --contrib-level-3: #26a641;
    --contrib-level-4: #39d353;
  }
}
</style>
