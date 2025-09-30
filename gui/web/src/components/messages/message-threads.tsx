'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { MessageItem } from './message-item'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface Thread {
  thread_id: string
  title: string
  channel_id?: string
  chat_id?: string
  created_at: string
  last_message_at: string
  message_count: number
  participants: string[]
  is_active: boolean
  is_archived: boolean
}

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

interface MessageThreadsProps {
  filters: MessageFilters
  refreshTrigger: number
}

export function MessageThreads({ filters, refreshTrigger }: MessageThreadsProps) {
  const [threads, setThreads] = useState<Thread[]>([])
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null)
  const [threadMessages, setThreadMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newThreadTitle, setNewThreadTitle] = useState('')

  const fetchThreads = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams()
      if (filters.channel_id) params.append('channel_id', filters.channel_id)
      if (filters.chat_id) params.append('chat_id', filters.chat_id)

      const response = await fetch(`/api/messages/threads?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch threads: ${response.statusText}`)
      }

      const data = await response.json()
      setThreads(data)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch threads')
      console.error('Error fetching threads:', err)
    } finally {
      setLoading(false)
    }
  }, [filters])

  const fetchThreadMessages = useCallback(async (threadId: string) => {
    setMessagesLoading(true)

    try {
      const response = await fetch(`/api/messages/threads/${threadId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch thread messages: ${response.statusText}`)
      }

      const data = await response.json()
      setThreadMessages(data.messages)

    } catch (err) {
      console.error('Error fetching thread messages:', err)
      setThreadMessages([])
    } finally {
      setMessagesLoading(false)
    }
  }, [])

  const createThread = useCallback(async () => {
    if (!newThreadTitle.trim()) return

    try {
      const response = await fetch('/api/messages/threads', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: newThreadTitle,
          channel_id: filters.channel_id,
          chat_id: filters.chat_id
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to create thread: ${response.statusText}`)
      }

      setNewThreadTitle('')
      setShowCreateForm(false)
      fetchThreads() // Refresh threads list

    } catch (err) {
      console.error('Error creating thread:', err)
    }
  }, [newThreadTitle, filters, fetchThreads])

  useEffect(() => {
    fetchThreads()
  }, [fetchThreads, refreshTrigger])

  useEffect(() => {
    if (selectedThread) {
      fetchThreadMessages(selectedThread.thread_id)
    }
  }, [selectedThread, fetchThreadMessages])

  const formatTimestamp = (timestamp: string) => {
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
          <Button onClick={fetchThreads} variant="outline">
            Try Again
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Threads List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium">Message Threads</h3>
          <Button
            onClick={() => setShowCreateForm(!showCreateForm)}
            size="sm"
          >
            {showCreateForm ? 'Cancel' : 'New Thread'}
          </Button>
        </div>

        {/* Create Thread Form */}
        {showCreateForm && (
          <Card className="p-4">
            <div className="space-y-3">
              <Input
                placeholder="Thread title..."
                value={newThreadTitle}
                onChange={(e) => setNewThreadTitle(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && createThread()}
              />
              <div className="flex space-x-2">
                <Button onClick={createThread} size="sm">
                  Create
                </Button>
                <Button 
                  onClick={() => setShowCreateForm(false)} 
                  variant="outline" 
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Threads */}
        {threads.length === 0 ? (
          <Card className="p-6">
            <div className="text-center text-muted-foreground">
              No threads found. Create a new thread to get started.
            </div>
          </Card>
        ) : (
          <div className="space-y-2">
            {threads.map((thread) => (
              <Card
                key={thread.thread_id}
                className={`p-4 cursor-pointer transition-colors ${
                  selectedThread?.thread_id === thread.thread_id
                    ? 'bg-blue-50 border-blue-200'
                    : 'hover:bg-gray-50'
                }`}
                onClick={() => setSelectedThread(thread)}
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between">
                    <h4 className="font-medium truncate">{thread.title}</h4>
                    <div className="flex items-center space-x-1">
                      {thread.is_active ? (
                        <Badge className="bg-green-100 text-green-800">Active</Badge>
                      ) : (
                        <Badge variant="outline">Inactive</Badge>
                      )}
                      {thread.is_archived && (
                        <Badge variant="outline">Archived</Badge>
                      )}
                    </div>
                  </div>
                  
                  <div className="text-sm text-muted-foreground">
                    <div className="flex items-center justify-between">
                      <span>{thread.message_count} messages</span>
                      <span>{formatTimestamp(thread.last_message_at)}</span>
                    </div>
                    
                    {(thread.channel_id || thread.chat_id) && (
                      <div className="mt-1 text-xs">
                        {thread.channel_id && (
                          <span>Channel: {thread.channel_id.substring(0, 12)}...</span>
                        )}
                        {thread.chat_id && (
                          <span className="ml-2">Chat: {thread.chat_id}</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Thread Messages */}
      <div className="space-y-4">
        {selectedThread ? (
          <>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-medium">{selectedThread.title}</h3>
                <p className="text-sm text-muted-foreground">
                  {selectedThread.message_count} messages
                </p>
              </div>
              <Button
                onClick={() => setSelectedThread(null)}
                variant="outline"
                size="sm"
              >
                Close
              </Button>
            </div>

            {messagesLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : threadMessages.length === 0 ? (
              <Card className="p-6">
                <div className="text-center text-muted-foreground">
                  No messages in this thread yet.
                </div>
              </Card>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {threadMessages.map((message) => (
                  <MessageItem key={message.id} message={message} />
                ))}
              </div>
            )}
          </>
        ) : (
          <Card className="p-6">
            <div className="text-center text-muted-foreground">
              Select a thread to view its messages
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}