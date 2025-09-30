'use client'

import { useState, useEffect, useCallback } from 'react'
import { ChannelList } from '@/components/channels/channel-list'
import { ChannelForm } from '@/components/channels/channel-form'
import { ChannelAnalyzer } from '@/components/channels/channel-analyzer'
import { ChannelTester } from '@/components/channels/channel-tester'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useWebSocket } from '@/hooks/use-websocket'

interface Channel {
  channel_id: string
  channel_name: string
  status: string
  last_processed?: string
  video_count: number
  error_message?: string
}

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<'list' | 'create' | 'edit' | 'analyze' | 'test'>('list')
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  // WebSocket connection for real-time updates
  const { isConnected, lastMessage } = useWebSocket('/ws/channels')

  // Handle real-time channel updates
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'channel_update') {
      // Trigger refresh when channel configurations change
      setRefreshTrigger(prev => prev + 1)
    }
  }, [lastMessage])

  const fetchChannels = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/channels', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch channels: ${response.statusText}`)
      }

      const data = await response.json()
      setChannels(data.channels)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch channels')
      console.error('Error fetching channels:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels, refreshTrigger])

  const handleChannelAction = useCallback((action: string, channelName?: string) => {
    switch (action) {
      case 'create':
        setActiveView('create')
        setSelectedChannel(null)
        break
      case 'edit':
        setActiveView('edit')
        setSelectedChannel(channelName || null)
        break
      case 'analyze':
        setActiveView('analyze')
        setSelectedChannel(channelName || null)
        break
      case 'test':
        setActiveView('test')
        setSelectedChannel(channelName || null)
        break
      case 'refresh':
        setRefreshTrigger(prev => prev + 1)
        break
      case 'back':
        setActiveView('list')
        setSelectedChannel(null)
        break
    }
  }, [])

  const handleChannelSaved = useCallback(() => {
    setActiveView('list')
    setSelectedChannel(null)
    setRefreshTrigger(prev => prev + 1)
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Channels</h1>
          <p className="text-muted-foreground">
            Manage YouTube channel configurations and monitoring
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-muted-foreground">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
          {activeView !== 'list' && (
            <Button onClick={() => handleChannelAction('back')} variant="outline" size="sm">
              Back to List
            </Button>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      {activeView === 'list' && (
        <div className="flex space-x-1 bg-muted p-1 rounded-lg">
          <Button
            variant="default"
            size="sm"
            onClick={() => setActiveView('list')}
          >
            Channel List
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleChannelAction('create')}
          >
            Add Channel
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleChannelAction('analyze')}
          >
            Smart Analyzer
          </Button>
        </div>
      )}

      {/* Content based on active view */}
      <div className="space-y-4">
        {activeView === 'list' && (
          <ChannelList 
            channels={channels}
            loading={loading}
            error={error}
            onChannelAction={handleChannelAction}
            onRefresh={() => handleChannelAction('refresh')}
          />
        )}
        
        {(activeView === 'create' || activeView === 'edit') && (
          <ChannelForm 
            mode={activeView}
            channelName={selectedChannel}
            onSaved={handleChannelSaved}
            onCancel={() => handleChannelAction('back')}
          />
        )}
        
        {activeView === 'analyze' && (
          <ChannelAnalyzer 
            onChannelAnalyzed={handleChannelSaved}
            onCancel={() => handleChannelAction('back')}
          />
        )}
        
        {activeView === 'test' && selectedChannel && (
          <ChannelTester 
            channelName={selectedChannel}
            onClose={() => handleChannelAction('back')}
          />
        )}
      </div>

      {/* Quick Stats */}
      {activeView === 'list' && channels.length > 0 && (
        <Card className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-600">
                {channels.length}
              </div>
              <div className="text-sm text-muted-foreground">Total Channels</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">
                {channels.filter(c => c.status === 'active').length}
              </div>
              <div className="text-sm text-muted-foreground">Active</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">
                {channels.filter(c => c.status === 'error').length}
              </div>
              <div className="text-sm text-muted-foreground">Errors</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-600">
                {channels.reduce((sum, c) => sum + c.video_count, 0)}
              </div>
              <div className="text-sm text-muted-foreground">Total Videos</div>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}