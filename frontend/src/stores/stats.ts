import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

interface DailyRequest {
  date: string
  count: number
}

interface DailyRequestStats {
  data: DailyRequest[]
  total_requests: number
  active_days: number
  max_count: number
  start_date: string
  end_date: string
}

export const useStatsStore = defineStore('stats', () => {
  // State
  const dailyRequests = ref<DailyRequest[]>([])
  const totalRequests = ref(0)
  const activeDays = ref(0)
  const maxCount = ref(0)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const heatmapData = computed(() => {
    return dailyRequests.value.map(item => ({
      date: item.date,
      count: item.count,
      level: getContributionLevel(item.count, maxCount.value)
    }))
  })

  const groupedByWeek = computed(() => {
    const weeks: DailyRequest[][] = []
    let currentWeek: DailyRequest[] = []
    
    for (const day of dailyRequests.value) {
      const date = new Date(day.date)
      const dayOfWeek = date.getDay()
      
      if (dayOfWeek === 0 && currentWeek.length > 0) {
        weeks.push([...currentWeek])
        currentWeek = []
      }
      
      currentWeek.push(day)
    }
    
    if (currentWeek.length > 0) {
      weeks.push(currentWeek)
    }
    
    return weeks
  })

  // Actions
  function getContributionLevel(count: number, max: number): number {
    if (count === 0) return 0
    if (max === 0) return 1
    
    const percentage = count / max
    if (percentage <= 0.25) return 1
    if (percentage <= 0.5) return 2
    if (percentage <= 0.75) return 3
    return 4
  }

  async function fetchDailyRequests(days: number = 365) {
    isLoading.value = true
    error.value = null
    
    try {
      const response = await axios.get<DailyRequestStats>(`/api/stats/daily-requests?days=${days}`)
      dailyRequests.value = response.data.data
      totalRequests.value = response.data.total_requests
      activeDays.value = response.data.active_days
      maxCount.value = response.data.max_count
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch daily request statistics'
      console.error('Failed to fetch daily requests:', e)
    } finally {
      isLoading.value = false
    }
  }

  function formatDate(dateStr: string): string {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    })
  }

  return {
    dailyRequests,
    totalRequests,
    activeDays,
    maxCount,
    isLoading,
    error,
    heatmapData,
    groupedByWeek,
    fetchDailyRequests,
    formatDate
  }
})
