'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Send, Bot, User, Video, Clock, ThumbsUp, ThumbsDown, Copy, ExternalLink } from 'lucide-react'
import { useWebSocket } from '@/hooks/use-websocket'

interface QnAExchange {
  id: string
  question: string
  answer: string
  timestamp: string
  contextVideos: Array<{
    id: string
    title: string
    url: string
    relevanceScore: number
  }>
  channelContext?: string
  confidenceScore: number
  followUpSuggestions: string[]
  conversationId: string
  responseTime: number
}

interface Channel {
  id: string
  name: string
  displayName: string
}

export function QnAChat() {
  const [question, setQuestion] = useState('')
  const [exchanges, setExchanges] = useState<QnAExchange[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedChannel, setSelectedChannel] = useState<string>('all')
  const [channels, setChannels] = useState<Channel[]>([])
  const [conversationId, setConversationId] = useState<string>('')
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const { sendMessage, lastMessage } = useWebSocket('/ws/qna')

  useEffect(() => {
    fetchChannels()
    generateConversationId()
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'qna_response') {
      const exchange = lastMessage.data as QnAExchange
      setExchanges(prev => [...prev, exchange])
      setIsLoading(false)
      scrollToBottom()
    }
  }, [lastMessage])

  useEffect(() => {
    scrollToBottom()
  }, [exchanges])

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

  const generateConversationId = () => {
    const id = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    setConversationId(id)
  }

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || isLoading) return

    const currentQuestion = question.trim()
    setQuestion('')
    setIsLoading(true)

    // Add user question to exchanges
    const userExchange: Partial<QnAExchange> = {
      id: `user_${Date.now()}`,
      question: currentQuestion,
      timestamp: new Date().toISOString(),
      channelContext: selectedChannel === 'all' ? undefined : selectedChannel
    }

    setExchanges(prev => [...prev, userExchange as QnAExchange])

    try {
      // Send via WebSocket for real-time response
      sendMessage({
        type: 'qna_question',
        data: {
          question: currentQuestion,
          channelContext: selectedChannel === 'all' ? null : selectedChannel,
          conversationId,
          interfaceSource: 'web'
        }
      })

      // Also send via HTTP API as fallback
      const response = await fetch('/api/qna/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: currentQuestion,
          channel_context: selectedChannel === 'all' ? null : selectedChannel,
          conversation_id: conversationId,
          interface_source: 'web'
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      // If WebSocket didn't provide response, use HTTP response
      if (!lastMessage || lastMessage.type !== 'qna_response') {
        const data = await response.json()
        setExchanges(prev => [...prev, data])
        setIsLoading(false)
      }
    } catch (error) {
      console.error('Failed to ask question:', error)
      setIsLoading(false)
      
      // Add error message
      const errorExchange: QnAExchange = {
        id: `error_${Date.now()}`,
        question: currentQuestion,
        answer: 'Sorry, I encountered an error processing your question. Please try again.',
        timestamp: new Date().toISOString(),
        contextVideos: [],
        confidenceScore: 0,
        followUpSuggestions: [],
        conversationId,
        responseTime: 0
      }
      setExchanges(prev => [...prev, errorExchange])
    }

    scrollToBottom()
  }

  const handleFollowUp = (suggestion: string) => {
    setQuestion(suggestion)
  }

  const handleFeedback = async (exchangeId: string, isPositive: boolean) => {
    try {
      await fetch(`/api/qna/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          exchange_id: exchangeId,
          is_positive: isPositive
        }),
      })
    } catch (error) {
      console.error('Failed to submit feedback:', error)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-4">
        <Select value={selectedChannel} onValueChange={setSelectedChannel}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Select channel" />
          </SelectTrigger>
          <SelectContent>
            {channels.map((channel) => (
              <SelectItem key={channel.id} value={channel.id}>
                {channel.displayName}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Badge variant="outline">
          Conversation: {conversationId.split('_')[1]}
        </Badge>
      </div>

      <Card className="h-96">
        <ScrollArea ref={scrollAreaRef} className="h-full p-4">
          <div className="space-y-4">
            {exchanges.length === 0 && (
              <div className="text-center text-muted-foreground py-8">
                <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Ask me anything about the processed videos!</p>
                <p className="text-sm mt-2">I can search through summaries and subtitles to find relevant information.</p>
              </div>
            )}

            {exchanges.map((exchange) => (
              <div key={exchange.id} className="space-y-3">
                {/* User Question */}
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="bg-muted rounded-lg p-3">
                      <p className="text-sm">{exchange.question}</p>
                    </div>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(exchange.timestamp)}
                      </span>
                      {exchange.channelContext && (
                        <Badge variant="secondary" className="text-xs">
                          {channels.find(ch => ch.id === exchange.channelContext)?.displayName || exchange.channelContext}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>

                {/* Bot Answer */}
                {exchange.answer && (
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center">
                        <Bot className="h-4 w-4 text-secondary-foreground" />
                      </div>
                    </div>
                    <div className="flex-1 space-y-3">
                      <div className="bg-background border rounded-lg p-3">
                        <p className="text-sm whitespace-pre-wrap">{exchange.answer}</p>
                      </div>

                      {/* Context Videos */}
                      {exchange.contextVideos && exchange.contextVideos.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-muted-foreground">Related Videos:</p>
                          <div className="space-y-1">
                            {exchange.contextVideos.map((video) => (
                              <div key={video.id} className="flex items-center justify-between p-2 bg-muted/50 rounded text-xs">
                                <div className="flex items-center space-x-2">
                                  <Video className="h-3 w-3" />
                                  <span className="truncate max-w-48">{video.title}</span>
                                  <Badge variant="outline" className="text-xs">
                                    {Math.round(video.relevanceScore * 100)}%
                                  </Badge>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 w-6 p-0"
                                  onClick={() => window.open(video.url, '_blank')}
                                >
                                  <ExternalLink className="h-3 w-3" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Follow-up Suggestions */}
                      {exchange.followUpSuggestions && exchange.followUpSuggestions.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-muted-foreground">Follow-up Questions:</p>
                          <div className="flex flex-wrap gap-1">
                            {exchange.followUpSuggestions.map((suggestion, index) => (
                              <Button
                                key={index}
                                variant="outline"
                                size="sm"
                                className="text-xs h-6"
                                onClick={() => handleFollowUp(suggestion)}
                              >
                                {suggestion}
                              </Button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Metadata and Actions */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3 text-xs text-muted-foreground">
                          {exchange.responseTime > 0 && (
                            <div className="flex items-center space-x-1">
                              <Clock className="h-3 w-3" />
                              <span>{exchange.responseTime}s</span>
                            </div>
                          )}
                          {exchange.confidenceScore > 0 && (
                            <Badge variant={exchange.confidenceScore > 0.8 ? "default" : "secondary"} className="text-xs">
                              {Math.round(exchange.confidenceScore * 100)}% confidence
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center space-x-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => copyToClipboard(exchange.answer)}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => handleFeedback(exchange.id, true)}
                          >
                            <ThumbsUp className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={() => handleFeedback(exchange.id, false)}
                          >
                            <ThumbsDown className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <Separator className="my-4" />
              </div>
            ))}

            {isLoading && (
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center">
                    <Bot className="h-4 w-4 text-secondary-foreground animate-pulse" />
                  </div>
                </div>
                <div className="flex-1">
                  <div className="bg-background border rounded-lg p-3">
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                      <span className="text-sm text-muted-foreground">Thinking...</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </Card>

      <form onSubmit={handleSubmit} className="flex space-x-2">
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about the videos..."
          disabled={isLoading}
          className="flex-1"
        />
        <Button type="submit" disabled={isLoading || !question.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  )
}