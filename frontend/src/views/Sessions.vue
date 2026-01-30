<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '../stores/sessions'

const router = useRouter()
const sessionStore = useSessionStore()

onMounted(() => {
  sessionStore.fetchSessions()
})

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`
}

function formatDate(date: string): string {
  return new Date(date).toLocaleString()
}

function viewSession(sessionId: string) {
  router.push(`/sessions/${sessionId}`)
}
</script>

<template>
  <div class="sessions-page">
    <div class="page-header">
      <h1>Sessions</h1>
      <button class="secondary" @click="sessionStore.fetchSessions()">
        🔄 Refresh
      </button>
    </div>

    <div v-if="sessionStore.loading" class="loading">
      Loading sessions...
    </div>

    <div v-else-if="sessionStore.error" class="error">
      Error: {{ sessionStore.error }}
    </div>

    <div v-else class="sessions-list">
      <div
        v-for="session in sessionStore.sessions"
        :key="session.session_id"
        class="card session-card"
        @click="viewSession(session.session_id)"
      >
        <div class="session-header">
          <div class="session-title">
            {{ session.title || `Session ${session.session_id}` }}
          </div>
          <span class="badge" :class="session.state">{{ session.state }}</span>
        </div>

        <div class="session-details">
          <div class="detail">
            <span class="label">ID</span>
            <code>{{ session.session_id }}</code>
          </div>
          <div class="detail">
            <span class="label">User</span>
            <span>{{ session.user_id }}</span>
          </div>
          <div class="detail">
            <span class="label">Messages</span>
            <span>{{ session.message_count }}</span>
          </div>
          <div class="detail">
            <span class="label">Cost</span>
            <span>{{ formatCost(session.total_cost) }}</span>
          </div>
        </div>

        <div class="session-meta">
          <div class="directory">
            📁 {{ session.working_directory }}
          </div>
          <div class="time">
            Updated: {{ formatDate(session.updated_at) }}
          </div>
        </div>
      </div>

      <div v-if="sessionStore.sessions.length === 0" class="empty card">
        <p>No sessions found.</p>
        <p>Start a new session by sending a message to the Telegram bot.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.sessions-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.session-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.session-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.session-title {
  font-size: 1.125rem;
  font-weight: 600;
}

.session-details {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: var(--bg-dark);
  border-radius: 0.5rem;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail .label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.detail code {
  font-size: 0.875rem;
}

.session-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.directory {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60%;
}

.badge.idle {
  background: rgba(34, 197, 94, 0.2);
  color: var(--success);
}

.badge.processing {
  background: rgba(234, 179, 8, 0.2);
  color: var(--warning);
}

.badge.error {
  background: rgba(239, 68, 68, 0.2);
  color: var(--error);
}

.loading, .error, .empty {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
}

.error {
  color: var(--error);
}

@media (max-width: 768px) {
  .session-details {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
