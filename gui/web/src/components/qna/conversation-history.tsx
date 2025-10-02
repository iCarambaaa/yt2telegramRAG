'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Search, MessageCircle, Calendar, Trash2, Download, Eye, Filter } from 'lucide-react'

interface ConversationSummary {
  sessionId: string
  channelContext?: string
  createdAt: string
  lastActivity: string
  exchangeCount: number
  firstQuestion: string
  tags: string[]
}

interface ConversationDetail {
  sessionId: string
  channelContext?: string
  createdAt: string
  lastActivity: string
  exchangeCount: number
  exchanges: Array<{
    id: string
    question: string
    answer: string
    timestamp: string
    confidenceScore: number
    contextVideos: Array<{
      id: string
      title: string
      url: string
    }>
  }>
}

export function ConversationHistory() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [filteredConversations, setFilteredConversations] = useState<ConversationSummary[]>([])
  const [selectedConversation, setSelectedConversation] = useState<ConversationDetail | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [channelFilter, setChannelFilter] = useState<string>('all')
  const [dateFilter, setDateFilter] = useState<string>('all')
  const [isLoading, setIsLoading] = useState(true)
  const [channels, setChannels] = useState<Array<{ id: string; name: string; displayName: string }>>([])

  useEffect(() => {
    fetchConversations()
    fetchChannels()
  }, [])

  useEffect(() => {
    filterConversations()
  }, [conversations, searchQuery, channelFilter, dateFilter])

  const fetchChannels = async () => {
    try {
      const response = await fetch('/api/channels')
      if (response.ok) {
        const data = await response.json()
        setChannels([
          { id: 'all', name: 'all', displayName: 'All Channels' },
          ...data.map((ch: any) => ({
            id: ch.channel_id,
            name: ch.channel_name,
            displayName: ch.display_name || ch.channel_name
          }))
        ])
      }
    } catch (error) {
      console.error('Failed to fetch channels:', error)
    }
  }

  const fetchConversations = async () => {
    try {
      setIsLoading(true)
      const response = await fetch('/api/qna/conversations')
      if (response.ok) {
        const data = await response.json()
        setConversations(data)
      }
    } catch (error) {
      console.error('Failed to fetch conversations:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchConversationDetail = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/qna/conversations/${sessionId}`)
      if (response.ok) {
        const data = await response.json()
        setSelectedConversation(data)
      }
    } catch (error) {
      console.error('Failed to fetch conversation detail:', error)
    }
  }

  const filterConversations = () => {
    let filtered = conversations

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(conv =>
        conv.firstQuestion.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conv.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    }

    // Channel filter
    if (channelFilter !== 'all') {
      filtered = filtered.filter(conv => conv.channelContext === channelFilter)
    }

    // Date filter
    if (dateFilter !== 'all') {
      const now = new Date()
      const filterDate = new Date()
      
      switch (dateFilter) {
        case 'today':
          filterDate.setHours(0, 0, 0, 0)
          break
        case 'week':
          filterDate.setDate(now.getDate() - 7)
          break
        case 'month':
          filterDate.setMonth(now.getMonth() - 1)
          break
      }
      
      if (dateFilter !== 'all') {
        filtered = filtered.filter(conv => new Date(conv.lastActivity) >= filterDate)
      }
    }

    setFilteredConversations(filtered)
  }

  const deleteConversation = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/qna/conversations/${sessionId}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        setConversations(prev => prev.filter(conv => conv.sessionId !== sessionId))
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    }
  }

  const exportConversation = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/qna/conversations/${sessionId}/export`)
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `conversation_${sessionId}.json`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }
    } catch (error) {
      console.error('Failed to export conversation:', error)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getChannelDisplayName = (channelId?: string) => {
    if (!channelId) return 'All Channels'
    const channel = channels.find(ch => ch.id === channelId)
    return channel?.displayName || channelId
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={channelFilter} onValueChange={setChannelFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by channel" />
          </SelectTrigger>
          <SelectContent>
            {channels.map((channel) => (
              <SelectItem key={channel.id} value={channel.id}>
                {channel.displayName}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={dateFilter} onValueChange={setDateFilter}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Date range" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Time</SelectItem>
            <SelectItem value="today">Today</SelectItem>
            <SelectItem value="week">This Week</SelectItem>
            <SelectItem value="month">This Month</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {filteredConversations.length} conversation{filteredConversations.length !== 1 ? 's' : ''} found
        </p>
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">
            {searchQuery || channelFilter !== 'all' || dateFilter !== 'all' ? 'Filtered' : 'All'}
          </span>
        </div>
      </div>

      {/* Conversations List */}
      <div className="space-y-3">
        {filteredConversations.length === 0 ? (
          <Card>
            <CardContent className="text-center py-8">
              <MessageCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-muted-foreground">No conversations found</p>
              <p className="text-sm text-muted-foreground mt-2">
                {searchQuery || channelFilter !== 'all' || dateFilter !== 'all'
                  ? 'Try adjusting your filters'
                  : 'Start asking questions to create conversation history'
                }
              </p>
            </CardContent>
          </Card>
        ) : (
          filteredConversations.map((conversation) => (
            <Card key={conversation.sessionId} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center space-x-2">
                      <h3 className="font-medium truncate max-w-md">
                        {conversation.firstQuestion}
                      </h3>
                      <Badge variant="secondary">
                        {conversation.exchangeCount} exchange{conversation.exchangeCount !== 1 ? 's' : ''}
                      </Badge>
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-3 w-3" />
                        <span>{formatDate(conversation.lastActivity)}</span>
                      </div>
                      {conversation.channelContext && (
                        <Badge variant="outline" className="text-xs">
                          {getChannelDisplayName(conversation.channelContext)}
                        </Badge>
                      )}
                    </div>

                    {conversation.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {conversation.tags.map((tag, index) => (
                          <Badge key={index} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-1 ml-4">
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => fetchConversationDetail(conversation.sessionId)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-4xl max-h-[80vh]">
                        <DialogHeader>
                          <DialogTitle>Conversation Details</DialogTitle>
                          <DialogDescription>
                            Session: {conversation.sessionId}
                          </DialogDescription>
                        </DialogHeader>
                        {selectedConversation && (
                          <ScrollArea className="h-96">
                            <div className="space-y-4">
                              {selectedConversation.exchanges.map((exchange, index) => (
                                <div key={exchange.id} className="space-y-2">
                                  <div className="bg-muted p-3 rounded-lg">
                                    <p className="font-medium text-sm">Q: {exchange.question}</p>
                                  </div>
                                  <div className="bg-background border p-3 rounded-lg">
                                    <p className="text-sm whitespace-pre-wrap">{exchange.answer}</p>
                                    {exchange.contextVideos.length > 0 && (
                                      <div className="mt-2 pt-2 border-t">
                                        <p className="text-xs font-medium text-muted-foreground mb-1">Related Videos:</p>
                                        <div className="space-y-1">
                                          {exchange.contextVideos.map((video) => (
                                            <div key={video.id} className="text-xs">
                                              <a href={video.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                                {video.title}
                                              </a>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                  {index < selectedConversation.exchanges.length - 1 && <Separator />}
                                </div>
                              ))}
                            </div>
                          </ScrollArea>
                        )}
                      </DialogContent>
                    </Dialog>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => exportConversation(conversation.sessionId)}
                    >
                      <Download className="h-4 w-4" />
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteConversation(conversation.sessionId)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}