<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useMemoryStore } from '../stores/memory'

const memoryStore = useMemoryStore()
const editContent = ref('')
const hasChanges = ref(false)

onMounted(() => {
  memoryStore.fetchFiles()
})

async function selectFile(filename: string) {
  await memoryStore.fetchFile(filename)
  if (memoryStore.currentFile) {
    editContent.value = memoryStore.currentFile.content
    hasChanges.value = false
  }
}

watch(editContent, (newVal) => {
  if (memoryStore.currentFile) {
    hasChanges.value = newVal !== memoryStore.currentFile.content
  }
})

async function saveFile() {
  if (!memoryStore.currentFile) return
  try {
    await memoryStore.saveFile(memoryStore.currentFile.filename, editContent.value)
    hasChanges.value = false
  } catch (e) {
    alert('Failed to save file')
  }
}

function discardChanges() {
  if (memoryStore.currentFile) {
    editContent.value = memoryStore.currentFile.content
    hasChanges.value = false
  }
}

function formatDate(date: string): string {
  return new Date(date).toLocaleString()
}
</script>

<template>
  <div class="memory-page">
    <h1>Memory Management</h1>
    <p class="subtitle">Edit AI agent memory files (SOUL.md, USER.md, etc.)</p>

    <div class="memory-layout">
      <div class="file-list card">
        <h2>Files</h2>
        <div v-if="memoryStore.loading" class="loading">Loading...</div>
        <div v-else class="files">
          <div
            v-for="file in memoryStore.files"
            :key="file.filename"
            class="file-item"
            :class="{ active: memoryStore.currentFile?.filename === file.filename }"
            @click="selectFile(file.filename)"
          >
            <div class="file-name">
              <span class="icon">{{ file.type === 'core' ? '📄' : '🧠' }}</span>
              {{ file.filename }}
            </div>
            <div class="file-meta">
              {{ formatDate(file.modified) }}
            </div>
          </div>
        </div>
      </div>

      <div class="editor-panel card">
        <div v-if="memoryStore.currentFile" class="editor">
          <div class="editor-header">
            <h2>{{ memoryStore.currentFile.filename }}</h2>
            <div class="editor-actions">
              <span v-if="hasChanges" class="unsaved">● Unsaved changes</span>
              <button
                class="secondary"
                :disabled="!hasChanges"
                @click="discardChanges"
              >
                Discard
              </button>
              <button
                class="primary"
                :disabled="!hasChanges || memoryStore.saving"
                @click="saveFile"
              >
                {{ memoryStore.saving ? 'Saving...' : 'Save' }}
              </button>
            </div>
          </div>
          <textarea
            v-model="editContent"
            class="editor-textarea"
            placeholder="File content..."
          ></textarea>
        </div>
        <div v-else class="empty-editor">
          <p>Select a file from the left to edit</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.memory-page h1 {
  margin-bottom: 0.5rem;
}

.subtitle {
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
}

.memory-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 1.5rem;
  height: calc(100vh - 200px);
}

.file-list {
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.file-list h2 {
  font-size: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border);
}

.files {
  flex: 1;
  overflow-y: auto;
}

.file-item {
  padding: 0.75rem;
  border-radius: 0.5rem;
  cursor: pointer;
  margin-bottom: 0.25rem;
  transition: background 0.2s;
}

.file-item:hover {
  background: var(--bg-dark);
}

.file-item.active {
  background: var(--primary);
}

.file-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.file-meta {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 0.25rem;
  margin-left: 1.5rem;
}

.file-item.active .file-meta {
  color: rgba(255, 255, 255, 0.7);
}

.editor-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border);
}

.editor-header h2 {
  font-size: 1rem;
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.unsaved {
  color: var(--warning);
  font-size: 0.875rem;
}

.editor-textarea {
  flex: 1;
  resize: none;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  padding: 1rem;
  border-radius: 0.5rem;
}

.empty-editor {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
}

.loading {
  text-align: center;
  padding: 2rem;
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .memory-layout {
    grid-template-columns: 1fr;
    height: auto;
  }

  .file-list {
    max-height: 200px;
  }

  .editor-panel {
    min-height: 400px;
  }
}
</style>
