'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Input } from '@/components/ui/input'

interface Channel {
  channel_id: string
  channel_name: string
  status: string
  last_processed?: string
  video_count: number
  error_message?: string
}

interface ChannelListProps {
  channels: Channel[]
  loading: boolean
  error: string | null
  onChannelAction: (action: string, channelName?: string) => void
  onRefresh: () => void
}

const STATUS_COLORS = {
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-gray-100 text-gray-800',
  error: 'bg-red-100 text-red-800',
  processing: 'bg-blue-100 text-blue-800'
}

const STATUS_LABELS = {
  active: 'Active',
  inactive: 'Inactive',
  error: 'Error',
  processing: 'Processing'
}

export function ChannelList({ channels, loading, error, onChannelAction, onRefresh }: ChannelListProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null)

  const filteredChannels = channels.filter(channel => {
    const matchesSearch = channel.channel_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         channel.channel_id.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || channel.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const handleDelete = async (channelName: string) => {
    try {
      const response = await fetch(`/api/channels/${channelName}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to delete channel: ${response.statusText}`)
      }

      setShowDeleteConfirm(null)
      onRefresh()

    } catch (err) {
      console.error('Error deleting channel:', err)
      alert('Failed to delete channel. Please try again.')
    }
  }

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'Never'
    return new Date(timestamp).toLocaleString()
  }

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner size="lg" />
      </div>
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
      {/* Controls */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <Input
              placeholder="Search channels..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="flex items-center space-x-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-input bg-background rounded-md text-sm"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="error">Error</option>
              <option value="processing">Processing</option>
            </select>
            <Button onClick={onRefresh} variant="outline" size="sm">
              Refresh
            </Button>
            <Button onClick={() => onChannelAction('create')} size="sm">
              Add Channel
            </Button>
          </div>
        </div>
      </Card>

      {/* Channel Cards */}
      {filteredChannels.length === 0 ? (
        <Card className="p-8">
          <div className="text-center text-muted-foreground">
            {channels.length === 0 ? (
              <div>
                <p className="mb-4">No channels configured yet.</p>
                <Button onClick={() => onChannelAction('create')}>
                  Add Your First Channel
                </Button>
              </div>
            ) : (
              <p>No channels match your search criteria.</p>
            )}
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredChannels.map((channel) => (
            <Card key={channel.channel_name} className="p-4 hover:shadow-md transition-shadow">
              <div className="space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium truncate">{channel.channel_name}</h3>
                    <p className="text-sm text-muted-foreground truncate">
                      {channel.channel_id}
                    </p>
                  </div>
                  <Badge 
                    className={STATUS_COLORS[channel.status as keyof typeof STATUS_COLORS] || 'bg-gray-100 text-gray-800'}
                  >
                    {STATUS_LABELS[channel.status as keyof typeof STATUS_LABELS] || channel.status}
                  </Badge>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Videos:</span>
                    <span className="ml-1 font-medium">{channel.video_count}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Last:</span>
                    <span className="ml-1 font-medium text-xs">
                      {formatTimestamp(channel.last_processed)}
                    </span>
                  </div>
                </div>

                {/* Error Message */}
                {channel.error_message && (
                  <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                    {channel.error_message}
                  </div>
                )}

                {/* Actions */}
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={() => onChannelAction('edit', channel.channel_name)}
                    variant="outline"
                    size="sm"
                  >
                    Edit
                  </Button>
                  <Button
                    onClick={() => onChannelAction('test', channel.channel_name)}
                    variant="outline"
                    size="sm"
                  >
                    Test
                  </Button>
                  <Button
                    onClick={() => onChannelAction('analyze', channel.channel_name)}
                    variant="outline"
                    size="sm"
                  >
                    Analyze
                  </Button>
                  
                  {showDeleteConfirm === channel.channel_name ? (
                    <div className="flex space-x-1">
                      <Button
                        onClick={() => handleDelete(channel.channel_name)}
                        variant="destructive"
                        size="sm"
                      >
                        Confirm
                      </Button>
                      <Button
                        onClick={() => setShowDeleteConfirm(null)}
                        variant="outline"
                        size="sm"
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      onClick={() => setShowDeleteConfirm(channel.channel_name)}
                      variant="outline"
                      size="sm"
                      className="text-red-600 hover:text-red-700"
                    >
                      Delete
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}