'use client'

import { useState, useEffect, useCallback } from 'react'
import { MessageHistory } from '@/components/messages/message-history'
import { MessageSearch } from '@/components/messages/message-search'
import { MessageFilters } from '@/components/messages/message-filters'
import { MessageThreads } from '@/components/messages/message-threads'
import { MessageExport } from '@/components/messages/message-export'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useWebSocket } from '@/hooks/use-websocket'

interface MessageFilters {
  channel_id?: string
  chat_id?: string
  message_type?: string
  thread_id?: string
  start_date?: string
  end_date?: string
}

export default function MessagesPage() {
  const [activeView, setActiveView] = useState<'history' | 'search' | 'threads' | 'export'>('history')
  const [filters, setFilters] = useState<MessageFilters>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  // WebSocket connection for real-time updates
  const { isConnected, lastMessage } = useWebSocket('/ws/messages')

  // Handle real-time message updates
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'message_update') {
      // Trigger refresh when new messages arrive
      setRefreshTrigger(prev => prev + 1)
    }
  }, [lastMessage])

  const handleFiltersChange = useCallback((newFilters: MessageFilters) => {
    setFilters(newFilters)
  }, [])

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query)
    setActiveView('search')
  }, [])

  const handleRefresh = useCallback(() => {
    setRefreshTrigger(prev => prev + 1)
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Messages</h1>
          <p className="text-muted-foreground">
            Browse and search Telegram message history
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
          variant={activeView === 'history' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('history')}
        >
          History
        </Button>
        <Button
          variant={activeView === 'search' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('search')}
        >
          Search
        </Button>
        <Button
          variant={activeView === 'threads' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveView('threads')}
        >
          Threads
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
      <Card className="p-4">
        <MessageFilters 
          filters={filters} 
          onFiltersChange={handleFiltersChange}
        />
      </Card>

      {/* Content based on active view */}
      <div className="space-y-4">
        {activeView === 'history' && (
          <MessageHistory 
            filters={filters}
            refreshTrigger={refreshTrigger}
            onSearch={handleSearch}
          />
        )}
        
        {activeView === 'search' && (
          <MessageSearch 
            query={searchQuery}
            filters={filters}
            onQueryChange={setSearchQuery}
          />
        )}
        
        {activeView === 'threads' && (
          <MessageThreads 
            filters={filters}
            refreshTrigger={refreshTrigger}
          />
        )}
        
        {activeView === 'export' && (
          <MessageExport 
            filters={filters}
          />
        )}
      </div>
    </div>
  )
}