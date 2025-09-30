'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'

interface MessageFilters {
  channel_id?: string
  chat_id?: string
  message_type?: string
  thread_id?: string
  start_date?: string
  end_date?: string
}

interface MessageFiltersProps {
  filters: MessageFilters
  onFiltersChange: (filters: MessageFilters) => void
}

const MESSAGE_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'telegram_out', label: 'Outgoing Telegram' },
  { value: 'telegram_in', label: 'Incoming Telegram' },
  { value: 'web_out', label: 'Web Interface' },
  { value: 'qna_question', label: 'QnA Question' },
  { value: 'qna_answer', label: 'QnA Answer' }
]

export function MessageFilters({ filters, onFiltersChange }: MessageFiltersProps) {
  const [localFilters, setLocalFilters] = useState<MessageFilters>(filters)
  const [isExpanded, setIsExpanded] = useState(false)

  useEffect(() => {
    setLocalFilters(filters)
  }, [filters])

  const handleFilterChange = (key: keyof MessageFilters, value: string) => {
    const newFilters = {
      ...localFilters,
      [key]: value || undefined
    }
    setLocalFilters(newFilters)
  }

  const applyFilters = () => {
    onFiltersChange(localFilters)
  }

  const clearFilters = () => {
    const emptyFilters = {}
    setLocalFilters(emptyFilters)
    onFiltersChange(emptyFilters)
  }

  const hasActiveFilters = Object.values(localFilters).some(value => value)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Label className="text-sm font-medium">Filters</Label>
          {hasActiveFilters && (
            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
              Active
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? 'Collapse' : 'Expand'}
        </Button>
      </div>

      {isExpanded && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="channel_id">Channel ID</Label>
            <Input
              id="channel_id"
              placeholder="UC123456789..."
              value={localFilters.channel_id || ''}
              onChange={(e) => handleFilterChange('channel_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="chat_id">Chat ID</Label>
            <Input
              id="chat_id"
              placeholder="@channel_name or -123456789"
              value={localFilters.chat_id || ''}
              onChange={(e) => handleFilterChange('chat_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="message_type">Message Type</Label>
            <select
              id="message_type"
              className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm"
              value={localFilters.message_type || ''}
              onChange={(e) => handleFilterChange('message_type', e.target.value)}
            >
              {MESSAGE_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="thread_id">Thread ID</Label>
            <Input
              id="thread_id"
              placeholder="thread_abc123..."
              value={localFilters.thread_id || ''}
              onChange={(e) => handleFilterChange('thread_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="start_date">Start Date</Label>
            <Input
              id="start_date"
              type="datetime-local"
              value={localFilters.start_date || ''}
              onChange={(e) => handleFilterChange('start_date', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="end_date">End Date</Label>
            <Input
              id="end_date"
              type="datetime-local"
              value={localFilters.end_date || ''}
              onChange={(e) => handleFilterChange('end_date', e.target.value)}
            />
          </div>
        </div>
      )}

      {isExpanded && (
        <div className="flex space-x-2 pt-4 border-t">
          <Button onClick={applyFilters} size="sm">
            Apply Filters
          </Button>
          <Button onClick={clearFilters} variant="outline" size="sm">
            Clear All
          </Button>
        </div>
      )}
    </div>
  )
}