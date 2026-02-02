<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const config = ref<any>(null)
const loading = ref(true)

async function fetchConfig() {
  loading.value = true
  try {
    const response = await axios.get('/api/config')
    config.value = response.data
  } catch (e) {
    console.error('Failed to fetch config:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchConfig)
</script>

<template>
  <div class="settings-page">
    <h1>Settings</h1>
    <p class="subtitle">View current configuration (edit .env file to change)</p>

    <div v-if="loading" class="loading">Loading configuration...</div>

    <div v-else-if="config" class="settings-content">
      <div class="card">
        <h2>Claude Code Settings</h2>
        <div class="settings-group">
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Approved Directory</span>
              <span class="setting-desc">Base directory for project access</span>
            </div>
            <code>{{ config.approved_directory }}</code>
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Workspace Path</span>
              <span class="setting-desc">AI agent memory storage location</span>
            </div>
            <code>{{ config.workspace_path }}</code>
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Timeout</span>
              <span class="setting-desc">Maximum execution time per request</span>
            </div>
            <span>{{ config.claude_timeout }} seconds</span>
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Max Turns</span>
              <span class="setting-desc">Maximum conversation turns per session</span>
            </div>
            <span>{{ config.claude_max_turns }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <h2>Rate Limiting</h2>
        <div class="settings-group">
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Request Limit</span>
              <span class="setting-desc">Maximum requests per time window</span>
            </div>
            <span>{{ config.rate_limit_requests }} requests</span>
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Time Window</span>
              <span class="setting-desc">Rate limit reset period</span>
            </div>
            <span>{{ config.rate_limit_window }} seconds</span>
          </div>
        </div>
      </div>

      <div class="card">
        <h2>Access Control</h2>
        <div class="settings-group">
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Allowed Users</span>
              <span class="setting-desc">Number of authorized Telegram users</span>
            </div>
            <span>{{ config.allowed_users_count }} users</span>
          </div>
        </div>
      </div>

      <div class="card info-card">
        <h2>Configuration Guide</h2>
        <div class="guide-content">
          <p>To modify settings, edit the <code>.env</code> file in the project root:</p>
          <pre>
# Telegram
TELEGRAM_BOT_TOKEN=your_token
ALLOWED_USERS=123456789,987654321

# Claude Code
CLAUDE_CLI_PATH=claude
APPROVED_DIRECTORY=/path/to/projects
CLAUDE_TIMEOUT=300
CLAUDE_MAX_TURNS=50

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
          </pre>
          <p>After editing, restart the service for changes to take effect.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page h1 {
  margin-bottom: 0.5rem;
}

.subtitle {
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 800px;
}

.card h2 {
  font-size: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-primary);
}

.settings-group {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border-primary);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.setting-label {
  font-weight: 500;
}

.setting-desc {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.setting-item code {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-card {
  background: var(--bg-secondary);
  border-color: var(--border-secondary);
}

.guide-content {
  font-size: 0.875rem;
}

.guide-content p {
  margin-bottom: 1rem;
}

.guide-content pre {
  margin: 1rem 0;
  padding: 1rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: 2px;
  overflow-x: auto;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
}
</style>
