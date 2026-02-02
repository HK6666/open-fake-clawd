<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useThemeStore } from './stores/theme'
import { Moon, Sun, Monitor } from 'lucide-vue-next'

const themeStore = useThemeStore()

const themeIcons = {
  light: Sun,
  dark: Moon,
  auto: Monitor
}

const themeLabels = {
  light: 'Light',
  dark: 'Dark',
  auto: 'Auto'
}
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
      <header class="top-bar">
        <div class="top-bar-spacer"></div>
        <button 
          class="theme-toggle" 
          @click="themeStore.toggleTheme"
          :title="`Theme: ${themeLabels[themeStore.theme]}`"
        >
          <component :is="themeIcons[themeStore.theme]" :size="18" />
          <span class="theme-label">{{ themeLabels[themeStore.theme] }}</span>
        </button>
      </header>
      <RouterView />
    </main>
  </div>
  
  <!-- Global tooltip for heatmap -->
  <div id="heatmap-tooltip"></div>
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

.top-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-primary);
}

.top-bar-spacer {
  flex: 1;
}

.theme-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.theme-toggle:hover {
  background: var(--hover-bg);
  border-color: var(--border-secondary);
  color: var(--text-primary);
}

.theme-label {
  font-size: 0.875rem;
}

@media (max-width: 768px) {
  .theme-label {
    display: none;
  }
  
  .theme-toggle {
    padding: 0.5rem;
  }
}
</style>
