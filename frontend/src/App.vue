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
          Dashboard
        </RouterLink>
        <RouterLink to="/sessions" class="nav-item">
          Sessions
        </RouterLink>
        <RouterLink to="/memory" class="nav-item">
          Memory
        </RouterLink>
        <RouterLink to="/settings" class="nav-item">
          Settings
        </RouterLink>
      </div>

      <div class="sidebar-footer">
        <a href="/docs" target="_blank" class="nav-item">
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
  border-right: 1px solid var(--border-primary);
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
  font-weight: 600;
  color: var(--text-primary);
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
  padding: 0.75rem 1rem;
  border-radius: 3px;
  color: var(--text-secondary);
  transition: all 0.15s;
  font-size: 0.9rem;
}

.nav-item:hover {
  background: var(--hover-bg);
  color: var(--text-primary);
  text-decoration: none;
}

.nav-item.router-link-active {
  background: var(--active-bg);
  color: var(--text-primary);
}

.sidebar-footer {
  border-top: 1px solid var(--border-primary);
  padding-top: 1rem;
}

.main-content {
  flex: 1;
  margin-left: 240px;
  padding: 2rem;
  min-height: 100vh;
}
</style>
