'use client'

import { useState, useEffect, useCallback } from 'react'
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

interface MessageSearchProps {
  query: string
  filters: MessageFilters
  onQueryChange: (query: string) => void
}

export function MessageSearch({ query, filters, onQueryChange }: MessageSearchProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchTime, setSearchTime] = useState<number | null>(null)
  const [localQuery, setLocalQuery] = useState(query)

  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setMessages([])
      setSearchTime(null)
      return
    }

    setLoading(true)
    setError(null)
    const startTime = Date.now()

    try {
      const params = new URLSearchParams({
        query: searchQuery,
        ...Object.fromEntries(
          Object.entries(filters).filter(([_, value]) => value)
        )
      })

      const response = await fetch(`/api/messages/search?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
      }

      const data = await response.json()
      setMessages(data.messages)
      setSearchTime(Date.now() - startTime)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      console.error('Search error:', err)
    } finally {
      setLoading(false)
    }
  }, [filters])

  // Perform search when query or filters change
  useEffect(() => {
    if (query) {
      setLocalQuery(query)
      performSearch(query)
    }
  }, [query, filters, performSearch])

  const handleSearch = () => {
    const trimmedQuery = localQuery.trim()
    if (trimmedQuery) {
      onQueryChange(trimmedQuery)
      performSearch(trimmedQuery)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const clearSearch = () => {
    setLocalQuery('')
    onQueryChange('')
    setMessages([])
    setSearchTime(null)
    setError(null)
  }

  return (
    <div className="space-y-4">
      {/* Search Input */}
      <Card className="p-4">
        <div className="flex space-x-2">
          <Input
            placeholder="Enter search query..."
            value={localQuery}
            onChange={(e) => setLocalQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1"
          />
          <Button onClick={handleSearch} disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </Button>
          {(localQuery || messages.length > 0) && (
            <Button onClick={clearSearch} variant="outline">
              Clear
            </Button>
          )}
        </div>
      </Card>

      {/* Search Info */}
      {(messages.length > 0 || searchTime !== null) && !loading && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Found {messages.length} result{messages.length !== 1 ? 's' : ''} for "{query}"
          </span>
          {searchTime !== null && (
            <span>
              Search completed in {searchTime}ms
            </span>
          )}
        </div>
      )}

      {/* Search Tips */}
      {!query && !loading && (
        <Card className="p-6">
          <div className="text-center space-y-4">
            <h3 className="text-lg font-medium">Search Messages</h3>
            <div className="text-sm text-muted-foreground space-y-2">
              <p>Enter keywords to search through message content.</p>
              <div className="text-left max-w-md mx-auto">
                <p className="font-medium mb-2">Search tips:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Use quotes for exact phrases: "error message"</li>
                  <li>Search is case-insensitive</li>
                  <li>Combine with filters for better results</li>
                  <li>Search includes message content and metadata</li>
                </ul>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {/* Error */}
      {error && (
        <Card className="p-6">
          <div className="text-center">
            <p className="text-red-600 mb-4">Error: {error}</p>
            <Button onClick={() => performSearch(query)} variant="outline">
              Try Again
            </Button>
          </div>
        </Card>
      )}

      {/* No Results */}
      {query && messages.length === 0 && !loading && !error && (
        <Card className="p-6">
          <div className="text-center text-muted-foreground">
            <p>No messages found for "{query}"</p>
            <p className="text-sm mt-2">Try different keywords or adjust your filters.</p>
          </div>
        </Card>
      )}

      {/* Search Results */}
      {messages.length > 0 && (
        <div className="space-y-2">
          {messages.map((message) => (
            <MessageItem key={message.id} message={message} />
          ))}
        </div>
      )}
    </div>
  )
}