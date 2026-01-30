<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-layout">
    <nav class="sidebar">
      <div class="logo">
        <h1>ccBot</h1>
        <span class="version">v0.1.0</span>
      </div>

      <div class="nav-links">
        <RouterLink to="/" class="nav-item">
          <span class="icon">📊</span>
          Dashboard
        </RouterLink>
        <RouterLink to="/sessions" class="nav-item">
          <span class="icon">💬</span>
          Sessions
        </RouterLink>
        <RouterLink to="/memory" class="nav-item">
          <span class="icon">🧠</span>
          Memory
        </RouterLink>
        <RouterLink to="/settings" class="nav-item">
          <span class="icon">⚙️</span>
          Settings
        </RouterLink>
      </div>

      <div class="sidebar-footer">
        <a href="/docs" target="_blank" class="nav-item">
          <span class="icon">📖</span>
          API Docs
        </a>
      </div>
    </nav>

    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  background: var(--bg-card);
  border-right: 1px solid var(--border);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
}

.logo {
  margin-bottom: 2rem;
}

.logo h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--primary);
}

.logo .version {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.nav-links {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.nav-item:hover {
  background: var(--bg-dark);
  color: var(--text-primary);
  text-decoration: none;
}

.nav-item.router-link-active {
  background: var(--primary);
  color: white;
}

.nav-item .icon {
  font-size: 1.25rem;
}

.sidebar-footer {
  border-top: 1px solid var(--border);
  padding-top: 1rem;
}

.main-content {
  flex: 1;
  margin-left: 240px;
  padding: 2rem;
  min-height: 100vh;
}
</style>
