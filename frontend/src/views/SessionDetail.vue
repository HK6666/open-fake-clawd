<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '../stores/sessions'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()

const sessionId = computed(() => route.params.id as string)

onMounted(() => {
  sessionStore.fetchSession(sessionId.value)
})

function formatDate(date: string): string {
  return new Date(date).toLocaleString()
}

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`
}

async function exportSession() {
  window.open(`/api/sessions/${sessionId.value}/export`, '_blank')
}

function goBack() {
  router.push('/sessions')
}
</script>

<template>
  <div class="session-detail">
    <div class="page-header">
      <button class="secondary" @click="goBack">← Back</button>
      <h1>Session Detail</h1>
      <button class="primary" @click="exportSession">Export</button>
    </div>

    <div v-if="sessionStore.loading" class="loading">
      Loading session...
    </div>

    <div v-else-if="sessionStore.error" class="error">
      Error: {{ sessionStore.error }}
    </div>

    <div v-else-if="sessionStore.currentSession" class="session-content">
      <div class="card info-card">
        <div class="info-grid">
          <div class="info-item">
            <span class="label">Session ID</span>
            <code>{{ sessionStore.currentSession.session_id }}</code>
          </div>
          <div class="info-item">
            <span class="label">Status</span>
            <span class="badge" :class="sessionStore.currentSession.state">
              {{ sessionStore.currentSession.state }}
            </span>
          </div>
          <div class="info-item">
            <span class="label">User ID</span>
            <span>{{ sessionStore.currentSession.user_id }}</span>
          </div>
          <div class="info-item">
            <span class="label">Total Cost</span>
            <span>{{ formatCost(sessionStore.currentSession.total_cost) }}</span>
          </div>
          <div class="info-item full-width">
            <span class="label">Working Directory</span>
            <code>{{ sessionStore.currentSession.working_directory }}</code>
          </div>
          <div class="info-item">
            <span class="label">Created</span>
            <span>{{ formatDate(sessionStore.currentSession.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="label">Updated</span>
            <span>{{ formatDate(sessionStore.currentSession.updated_at) }}</span>
          </div>
        </div>
      </div>

      <div class="card messages-card">
        <h2>Conversation ({{ sessionStore.currentSession.messages.length }} messages)</h2>

        <div class="messages">
          <div
            v-for="(message, index) in sessionStore.currentSession.messages"
            :key="index"
            class="message"
            :class="message.role"
          >
            <div class="message-header">
              <span class="role">{{ message.role === 'user' ? 'User' : 'Assistant' }}</span>
              <span class="time">{{ formatDate(message.timestamp) }}</span>
            </div>
            <div class="message-content">
              <pre>{{ message.content }}</pre>
            </div>
          </div>

          <div v-if="sessionStore.currentSession.messages.length === 0" class="empty">
            No messages in this session yet.
          </div>
        </div>
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
  gap: 1rem;
}

.page-header h1 {
  flex: 1;
}

.session-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.info-card {
  padding: 1.5rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-item.full-width {
  grid-column: span 4;
}

.info-item .label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.info-item code {
  font-size: 0.875rem;
}

.messages-card h2 {
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-primary);
  font-size: 1.125rem;
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: 600px;
  overflow-y: auto;
}

.message {
  padding: 1rem;
  border-radius: 4px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
}

.message.user {
  border-left: 3px solid var(--text-primary);
}

.message.assistant {
  border-left: 3px solid var(--status-success);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

.role {
  font-weight: 500;
}

.time {
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.message-content pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.875rem;
  background: transparent;
  padding: 0;
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

.loading, .error, .empty {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
}

.error {
  color: var(--status-error);
}

@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .info-item.full-width {
    grid-column: span 2;
  }
}
</style>
