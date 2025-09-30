'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

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

interface MessageItemProps {
  message: Message
}

const MESSAGE_TYPE_COLORS = {
  telegram_out: 'bg-blue-100 text-blue-800',
  telegram_in: 'bg-green-100 text-green-800',
  web_out: 'bg-purple-100 text-purple-800',
  qna_question: 'bg-orange-100 text-orange-800',
  qna_answer: 'bg-yellow-100 text-yellow-800'
}

const MESSAGE_TYPE_LABELS = {
  telegram_out: 'Outgoing',
  telegram_in: 'Incoming',
  web_out: 'Web',
  qna_question: 'Question',
  qna_answer: 'Answer'
}

export function MessageItem({ message }: MessageItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showMetadata, setShowMetadata] = useState(false)

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  const formatContent = (content: string, formatting: Record<string, any>) => {
    // Basic markdown rendering for formatted content
    if (formatting.markdown) {
      return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
    }
    return content
  }

  const truncateContent = (content: string, maxLength: number = 200) => {
    if (content.length <= maxLength) return content
    return content.substring(0, maxLength) + '...'
  }

  const displayContent = isExpanded 
    ? formatContent(message.content, message.formatting)
    : truncateContent(message.content)

  const needsTruncation = message.content.length > 200

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-2">
            <Badge 
              className={MESSAGE_TYPE_COLORS[message.message_type as keyof typeof MESSAGE_TYPE_COLORS] || 'bg-gray-100 text-gray-800'}
            >
              {MESSAGE_TYPE_LABELS[message.message_type as keyof typeof MESSAGE_TYPE_LABELS] || message.message_type}
            </Badge>
            
            {message.thread_id && (
              <Badge variant="outline" className="text-xs">
                Thread: {message.thread_id.substring(0, 8)}...
              </Badge>
            )}
          </div>
          
          <div className="text-xs text-muted-foreground">
            {formatTimestamp(message.timestamp)}
          </div>
        </div>

        {/* Content */}
        <div className="space-y-2">
          <div 
            className="text-sm leading-relaxed"
            dangerouslySetInnerHTML={{ __html: displayContent }}
          />
          
          {needsTruncation && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-xs p-0 h-auto"
            >
              {isExpanded ? 'Show less' : 'Show more'}
            </Button>
          )}
        </div>

        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">
              Attachments ({message.attachments.length})
            </div>
            <div className="flex flex-wrap gap-2">
              {message.attachments.map((attachment, index) => (
                <Badge key={index} variant="outline" className="text-xs">
                  {attachment.type}: {attachment.filename || 'Unknown'}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center space-x-4">
            {message.channel_id && (
              <span>Channel: {message.channel_id.substring(0, 12)}...</span>
            )}
            {message.chat_id && (
              <span>Chat: {message.chat_id}</span>
            )}
            {message.user_id && (
              <span>User: {message.user_id}</span>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <span>ID: {message.id.substring(0, 8)}...</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowMetadata(!showMetadata)}
              className="text-xs p-0 h-auto"
            >
              {showMetadata ? 'Hide' : 'Show'} metadata
            </Button>
          </div>
        </div>

        {/* Metadata */}
        {showMetadata && (
          <div className="mt-3 p-3 bg-muted rounded-md">
            <div className="text-xs font-medium mb-2">Metadata</div>
            <pre className="text-xs text-muted-foreground overflow-x-auto">
              {JSON.stringify({
                id: message.id,
                metadata: message.metadata,
                formatting: message.formatting
              }, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </Card>
  )
}