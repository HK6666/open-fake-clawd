import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

type Theme = 'light' | 'dark' | 'auto'

export const useThemeStore = defineStore('theme', () => {
  // State
  const theme = ref<Theme>('auto')
  const isDark = ref(false)

  // Get saved theme from localStorage
  const savedTheme = localStorage.getItem('theme') as Theme | null
  if (savedTheme && ['light', 'dark', 'auto'].includes(savedTheme)) {
    theme.value = savedTheme
  }

  // Actions
  function setTheme(newTheme: Theme) {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)
    applyTheme()
  }

  function toggleTheme() {
    if (theme.value === 'light') {
      setTheme('dark')
    } else if (theme.value === 'dark') {
      setTheme('auto')
    } else {
      setTheme('light')
    }
  }

  function applyTheme() {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    
    if (theme.value === 'dark' || (theme.value === 'auto' && prefersDark)) {
      isDark.value = true
      document.documentElement.classList.add('dark')
      document.documentElement.classList.remove('light')
    } else {
      isDark.value = false
      document.documentElement.classList.remove('dark')
      document.documentElement.classList.add('light')
    }
  }

  // Watch for system theme changes when in auto mode
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (theme.value === 'auto') {
      applyTheme()
    }
  })

  // Initialize theme
  applyTheme()

  return {
    theme,
    isDark,
    setTheme,
    toggleTheme,
    applyTheme
  }
})
