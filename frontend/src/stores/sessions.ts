import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export interface Session {
  session_id: string
  user_id: number
  working_directory: string
  state: string
  created_at: string
  updated_at: string
  message_count: number
  total_cost: number
  title?: string
}

export interface Message {
  role: string
  content: string
  timestamp: string
}

export interface SessionDetail extends Session {
  messages: Message[]
}

export const useSessionStore = defineStore('sessions', () => {
  const sessions = ref<Session[]>([])
  const currentSession = ref<SessionDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchSessions() {
    loading.value = true
    error.value = null
    try {
      const response = await axios.get('/api/sessions')
      sessions.value = response.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchSession(sessionId: string) {
    loading.value = true
    error.value = null
    try {
      const response = await axios.get(`/api/sessions/${sessionId}`)
      currentSession.value = response.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  return {
    sessions,
    currentSession,
    loading,
    error,
    fetchSessions,
    fetchSession
  }
})
