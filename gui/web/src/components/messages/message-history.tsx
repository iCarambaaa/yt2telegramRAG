'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { MessageItem } from './message-item'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface Message {
  id: string
  content: string
  message_type: string
  channel_id?: string
  chat_id?: string
  timestamp: string
  user_id?: string
  thread_id?: string
  metadata: Record<string, any>
  formatting: Record<string, any>
  attachments: any[]
}

interface MessageFilters {
  channel_id?: string
  chat_id?: string
  message_type?: string
  thread_id?: string
  start_date?: string
  end_date?: string
}

interface MessageHistoryProps {
  filters: MessageFilters
  refreshTrigger: number
  onSearch: (query: string) => void
}

interface PaginationInfo {
  page: number
  page_size: number
  total_count: number
  has_next: boolean
}

export function MessageHistory({ filters, refreshTrigger, onSearch }: MessageHistoryProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    page_size: 50,
    total_count: 0,
    has_next: false
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [infiniteScrollEnabled, setInfiniteScrollEnabled] = useState(true)
  
  const observerRef = useRef<IntersectionObserver>()
  const lastMessageElementRef = useRef<HTMLDivElement>()

  const fetchMessages = useCallback(async (page: number = 1, append: boolean = false) => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pagination.page_size.toString(),
        ...Object.fromEntries(
          Object.entries(filters).filter(([_, value]) => value)
        )
      })

      const response = await fetch(`/api/messages?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch messages: ${response.statusText}`)
      }

      const data = await response.json()
      
      if (append) {
        setMessages(prev => [...prev, ...data.messages])
      } else {
        setMessages(data.messages)
      }
      
      setPagination({
        page: data.page,
        page_size: data.page_size || 50,
        total_count: data.total_count,
        has_next: data.has_next
      })

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch messages')
      console.error('Error fetching messages:', err)
    } finally {
      setLoading(false)
    }
  }, [filters, pagination.page_size])

  // Initial load and filter changes
  useEffect(() => {
    fetchMessages(1, false)
  }, [filters, refreshTrigger])

  // Infinite scroll setup
  useEffect(() => {
    if (!infiniteScrollEnabled || loading || !pagination.has_next) return

    if (observerRef.current) observerRef.current.disconnect()

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && pagination.has_next) {
          fetchMessages(pagination.page + 1, true)
        }
      },
      { threshold: 1.0 }
    )

    if (lastMessageElementRef.current) {
      observerRef.current.observe(lastMessageElementRef.current)
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [fetchMessages, infiniteScrollEnabled, loading, pagination.has_next, pagination.page])

  const handleSearch = () => {
    if (searchQuery.trim()) {
      onSearch(searchQuery.trim())
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const loadMore = () => {
    if (pagination.has_next && !loading) {
      fetchMessages(pagination.page + 1, true)
    }
  }

  const refresh = () => {
    fetchMessages(1, false)
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error: {error}</p>
          <Button onClick={refresh} variant="outline">
            Try Again
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <Card className="p-4">
        <div className="flex space-x-2">
          <Input
            placeholder="Search messages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1"
          />
          <Button onClick={handleSearch}>
            Search
          </Button>
        </div>
      </Card>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <span className="text-sm text-muted-foreground">
            {pagination.total_count} messages total
          </span>
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={infiniteScrollEnabled}
              onChange={(e) => setInfiniteScrollEnabled(e.target.checked)}
            />
            <span>Infinite scroll</span>
          </label>
        </div>
        <Button onClick={refresh} variant="outline" size="sm">
          Refresh
        </Button>
      </div>

      {/* Messages List */}
      <div className="space-y-2">
        {messages.length === 0 && !loading ? (
          <Card className="p-8">
            <div className="text-center text-muted-foreground">
              No messages found. Try adjusting your filters.
            </div>
          </Card>
        ) : (
          messages.map((message, index) => (
            <div
              key={message.id}
              ref={index === messages.length - 1 ? lastMessageElementRef : undefined}
            >
              <MessageItem message={message} />
            </div>
          ))
        )}
      </div>

      {/* Loading States */}
      {loading && (
        <div className="flex justify-center py-4">
          <LoadingSpinner />
        </div>
      )}

      {/* Manual Load More (when infinite scroll is disabled) */}
      {!infiniteScrollEnabled && pagination.has_next && !loading && (
        <div className="flex justify-center py-4">
          <Button onClick={loadMore} variant="outline">
            Load More Messages
          </Button>
        </div>
      )}

      {/* End of Messages */}
      {!pagination.has_next && messages.length > 0 && (
        <div className="text-center py-4 text-muted-foreground text-sm">
          End of messages
        </div>
      )}
    </div>
  )
}