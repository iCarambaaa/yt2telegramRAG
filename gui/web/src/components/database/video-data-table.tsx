'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

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

interface Pagination {
  page: number
  page_size: number
  total_count: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

interface VideoDataTableProps {
  videos: VideoRecord[]
  loading: boolean
  error: string | null
  pagination: Pagination
  onPageChange: (page: number) => void
  onVideoSelect: (videoId: string) => void
  onRefresh: () => void
}

const METHOD_COLORS = {
  single: 'bg-blue-100 text-blue-800',
  multi: 'bg-purple-100 text-purple-800'
}

export function VideoDataTable({ 
  videos, 
  loading, 
  error, 
  pagination, 
  onPageChange, 
  onVideoSelect, 
  onRefresh 
}: VideoDataTableProps) {
  const [sortField, setSortField] = useState<string>('processed_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  const formatDuration = (seconds: number) => {
    return `${seconds.toFixed(1)}s`
  }

  const formatCost = (cost: number) => {
    return `$${cost.toFixed(3)}`
  }

  const formatTokens = (tokens: number) => {
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`
    }
    return tokens.toString()
  }

  const truncateText = (text: string, maxLength: number = 50) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex justify-center">
          <LoadingSpinner size="lg" />
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error: {error}</p>
          <Button onClick={onRefresh} variant="outline">
            Try Again
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('title')}
                    className="flex items-center space-x-1 hover:text-foreground"
                  >
                    <span>Title</span>
                    {sortField === 'title' && (
                      <span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Channel
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('processed_at')}
                    className="flex items-center space-x-1 hover:text-foreground"
                  >
                    <span>Processed</span>
                    {sortField === 'processed_at' && (
                      <span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Method
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Model
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('processing_time_seconds')}
                    className="flex items-center space-x-1 hover:text-foreground"
                  >
                    <span>Time</span>
                    {sortField === 'processing_time_seconds' && (
                      <span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('cost_estimate')}
                    className="flex items-center space-x-1 hover:text-foreground"
                  >
                    <span>Cost</span>
                    {sortField === 'cost_estimate' && (
                      <span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </button>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Tokens
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-background divide-y divide-border">
              {videos.map((video) => (
                <tr key={video.id} className="hover:bg-muted/50">
                  <td className="px-4 py-4">
                    <div className="flex items-center">
                      <div>
                        <div className="text-sm font-medium text-foreground">
                          {truncateText(video.title)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {video.id}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="text-xs text-muted-foreground">
                      {video.channel_id.substring(0, 12)}...
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="text-xs text-muted-foreground">
                      {formatTimestamp(video.processed_at)}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <Badge 
                      className={METHOD_COLORS[video.summarization_method as keyof typeof METHOD_COLORS] || 'bg-gray-100 text-gray-800'}
                    >
                      {video.summarization_method}
                    </Badge>
                  </td>
                  <td className="px-4 py-4">
                    <div className="text-xs">
                      <div className="font-medium">{video.primary_model}</div>
                      {video.secondary_model && (
                        <div className="text-muted-foreground">
                          +{video.secondary_model}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="text-xs font-medium">
                      {formatDuration(video.processing_time_seconds)}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="text-xs font-medium">
                      {formatCost(video.cost_estimate)}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="text-xs">
                      <div>{formatTokens(video.token_usage.total_tokens)}</div>
                      <div className="text-muted-foreground">
                        {formatTokens(video.token_usage.input_tokens)}/
                        {formatTokens(video.token_usage.output_tokens)}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <Button
                      onClick={() => onVideoSelect(video.id)}
                      variant="outline"
                      size="sm"
                    >
                      View
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Pagination */}
      {pagination.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Showing {((pagination.page - 1) * pagination.page_size) + 1} to{' '}
            {Math.min(pagination.page * pagination.page_size, pagination.total_count)} of{' '}
            {pagination.total_count} results
          </div>
          <div className="flex items-center space-x-2">
            <Button
              onClick={() => onPageChange(pagination.page - 1)}
              disabled={!pagination.has_previous}
              variant="outline"
              size="sm"
            >
              Previous
            </Button>
            <span className="text-sm">
              Page {pagination.page} of {pagination.total_pages}
            </span>
            <Button
              onClick={() => onPageChange(pagination.page + 1)}
              disabled={!pagination.has_next}
              variant="outline"
              size="sm"
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {videos.length === 0 && !loading && (
        <Card className="p-8">
          <div className="text-center text-muted-foreground">
            No video records found. Try adjusting your filters.
          </div>
        </Card>
      )}
    </div>
  )
}