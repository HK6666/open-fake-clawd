<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useSessionStore } from '../stores/sessions'

const sessionStore = useSessionStore()

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
})

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`
}

function formatDate(date: string): string {
  return new Date(date).toLocaleString()
}
</script>

<template>
  <div class="dashboard">
    <h1>Dashboard</h1>

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
</style>
