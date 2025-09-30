'use client'

import { useState, useEffect, useCallback } from 'react'
import { VideoDataTable } from '@/components/database/video-data-table'
import { DatabaseFilters } from '@/components/database/database-filters'
import { DatabaseStatistics } from '@/components/database/database-statistics'
import { DatabaseExport } from '@/components/database/database-export'
import { VideoDetailsModal } from '@/components/database/video-details-modal'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useWebSocket } from '@/hooks/use-websocket'

interface VideoRecord {
  id: string
  title: string
  channel_id: string
  published_at: string
  processed_at: string
  summarization_method: string
  primary_model: string
  secondary_model?: string
  synthesis_model?: string
  processing_time_seconds: number
  cost_estimate: number
  token_usage: {
    input_tokens: number
    output_tokens: number
    total_tokens: number
  }
  has_summary: boolean
  summary_length: number
  fallback_used: boolean
}

interface DatabaseFilters {
  channel_id?: string
  search?: string
  sort_by?: string
  sort_order?: string
  date_from?: string
  date_to?: string
  has_summary?: boolean
  summarization_method?: string
}

export default function DatabasePage() {
  const [activeView, setActiveView] = useState<'table' | 'statistics' | 'export'>('table')
  const [videos, setVideos] = useState<VideoRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<DatabaseFilters>({})
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 50,
    total_count: 0,
    total_pages: 0,
    has_next: false,
    has_previous: false
  })
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  // WebSocket connection for real-time updates
  const { isConnected, lastMessage } = useWebSocket('/ws/database')

  // Handle real-time database updates
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'database_update') {
      // Trigger refresh when database changes
      setRefreshTrigger(prev => prev + 1)
    }
  }, [lastMessage])

  const fetchVideos = useCallback(async (page: number = 1) => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pagination.page_size.toString(),
        ...Object.fromEntries(
          Object.entries(filters).filter(([_, value]) => value !== undefined && value !== '')
        )
      })

      const response = await fetch(`/api/analytics/database/videos?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch videos: ${response.statusText}`)
      }

      const data = await response.json()
      setVideos(data.videos)
      setPagination(data.pagination)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch videos')
      console.error('Error fetching videos:', err)
    } finally {
      setLoading(false)
    }
  }, [filters, pagination.page_size])

  useEffect(() => {
    fetchVideos(1)
  }, [filters, refreshTrigger])

  const handleFiltersChange = useCallback((newFilters: DatabaseFilters) => {
    setFilters(newFilters)
  }, [])

  const handlePageChange = useCallback((newPage: number) => {
    fetchVideos(newPage)
  }, [fetchVideos])

  const handleVideoSelect = useCallback((videoId: string) => {
    setSelectedVideo(videoId)
  }, [])

  const handleRefresh = useCallback(() => {
    setRefreshTrigger(prev => prev + 1)
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Database Browser</h1>
          <p className="text-muted-foreground">
            Browse and analyze video processing records
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-muted-foreground">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
          <Button onClick={handleRefresh} variant="outline" size="sm">
            Refresh
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex space-x-1 bg-muted p-1 rounded-lg">
        <Button
          variant={activeView === 'table' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('table')}
        >
          Data Table
        </Button>
        <Button
          variant={activeView === 'statistics' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('statistics')}
        >
          Statistics
        </Button>
        <Button
          variant={activeView === 'export' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('export')}
        >
          Export
        </Button>
      </div>

      {/* Filters */}
      {activeView === 'table' && (
        <Card className="p-4">
          <DatabaseFilters 
            filters={filters} 
            onFiltersChange={handleFiltersChange}
          />
        </Card>
      )}

      {/* Content based on active view */}
      <div className="space-y-4">
        {activeView === 'table' && (
          <VideoDataTable 
            videos={videos}
            loading={loading}
            error={error}
            pagination={pagination}
            onPageChange={handlePageChange}
            onVideoSelect={handleVideoSelect}
            onRefresh={handleRefresh}
          />
        )}
        
        {activeView === 'statistics' && (
          <DatabaseStatistics 
            refreshTrigger={refreshTrigger}
          />
        )}
        
        {activeView === 'export' && (
          <DatabaseExport 
            filters={filters}
          />
        )}
      </div>

      {/* Quick Stats */}
      {activeView === 'table' && videos.length > 0 && (
        <Card className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-600">
                {pagination.total_count}
              </div>
              <div className="text-sm text-muted-foreground">Total Videos</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">
                {videos.filter(v => v.has_summary).length}
              </div>
              <div className="text-sm text-muted-foreground">With Summary</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-600">
                {videos.filter(v => v.summarization_method === 'multi').length}
              </div>
              <div className="text-sm text-muted-foreground">Multi-Model</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-600">
                ${videos.reduce((sum, v) => sum + v.cost_estimate, 0).toFixed(2)}
              </div>
              <div className="text-sm text-muted-foreground">Total Cost</div>
            </div>
          </div>
        </Card>
      )}

      {/* Video Details Modal */}
      {selectedVideo && (
        <VideoDetailsModal 
          videoId={selectedVideo}
          onClose={() => setSelectedVideo(null)}
        />
      )}
    </div>
  )
}