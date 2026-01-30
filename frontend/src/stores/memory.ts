import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export interface MemoryFile {
  filename: string
  path: string
  type: string
  modified: string
}

export const useMemoryStore = defineStore('memory', () => {
  const files = ref<MemoryFile[]>([])
  const currentFile = ref<{ filename: string; content: string } | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  async function fetchFiles() {
    loading.value = true
    error.value = null
    try {
      const response = await axios.get('/api/memory/files')
      files.value = response.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchFile(filename: string) {
    loading.value = true
    error.value = null
    try {
      const response = await axios.get(`/api/memory/${filename}`)
      currentFile.value = response.data
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function saveFile(filename: string, content: string) {
    saving.value = true
    error.value = null
    try {
      await axios.put(`/api/memory/${filename}`, { content })
      if (currentFile.value && currentFile.value.filename === filename) {
        currentFile.value.content = content
      }
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      saving.value = false
    }
  }

  return {
    files,
    currentFile,
    loading,
    saving,
    error,
    fetchFiles,
    fetchFile,
    saveFile
  }
})
