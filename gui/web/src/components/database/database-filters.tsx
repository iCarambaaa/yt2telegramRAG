'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface DatabaseFilters {
  channel_id?: string
  search?: string
  sort_by?: string
  sort_order?: string
  date_from?: string
  date_to?: string
  has_summary?: boolean
  summarization_method?: string
}

interface DatabaseFiltersProps {
  filters: DatabaseFilters
  onFiltersChange: (filters: DatabaseFilters) => void
}

const SORT_OPTIONS = [
  { value: 'processed_at', label: 'Processed Date' },
  { value: 'published_at', label: 'Published Date' },
  { value: 'title', label: 'Title' },
  { value: 'cost_estimate', label: 'Cost' },
  { value: 'processing_time_seconds', label: 'Processing Time' }
]

const SUMMARIZATION_METHODS = [
  { value: '', label: 'All Methods' },
  { value: 'single', label: 'Single Model' },
  { value: 'multi', label: 'Multi-Model' }
]

export function DatabaseFilters({ filters, onFiltersChange }: DatabaseFiltersProps) {
  const [localFilters, setLocalFilters] = useState<DatabaseFilters>(filters)
  const [isExpanded, setIsExpanded] = useState(false)

  useEffect(() => {
    setLocalFilters(filters)
  }, [filters])

  const handleFilterChange = (key: keyof DatabaseFilters, value: any) => {
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

  const hasActiveFilters = Object.values(localFilters).some(value => value !== undefined && value !== '')

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

      {/* Quick Search */}
      <div className="flex space-x-2">
        <Input
          placeholder="Search videos..."
          value={localFilters.search || ''}
          onChange={(e) => handleFilterChange('search', e.target.value)}
          className="flex-1"
        />
        <Button onClick={applyFilters} size="sm">
          Search
        </Button>
      </div>

      {isExpanded && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="channel_id">Channel ID</Label>
            <Input
              id="channel_id"
              placeholder="UCbfYPyITQ-7l4upoX8nvctg"
              value={localFilters.channel_id || ''}
              onChange={(e) => handleFilterChange('channel_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="summarization_method">Summarization Method</Label>
            <select
              id="summarization_method"
              className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm"
              value={localFilters.summarization_method || ''}
              onChange={(e) => handleFilterChange('summarization_method', e.target.value)}
            >
              {SUMMARIZATION_METHODS.map((method) => (
                <option key={method.value} value={method.value}>
                  {method.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="has_summary">Has Summary</Label>
            <select
              id="has_summary"
              className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm"
              value={localFilters.has_summary === undefined ? '' : localFilters.has_summary.toString()}
              onChange={(e) => handleFilterChange('has_summary', e.target.value === '' ? undefined : e.target.value === 'true')}
            >
              <option value="">All Videos</option>
              <option value="true">With Summary</option>
              <option value="false">Without Summary</option>
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="sort_by">Sort By</Label>
            <select
              id="sort_by"
              className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm"
              value={localFilters.sort_by || 'processed_at'}
              onChange={(e) => handleFilterChange('sort_by', e.target.value)}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="sort_order">Sort Order</Label>
            <select
              id="sort_order"
              className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm"
              value={localFilters.sort_order || 'desc'}
              onChange={(e) => handleFilterChange('sort_order', e.target.value)}
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="date_from">Date From</Label>
            <Input
              id="date_from"
              type="date"
              value={localFilters.date_from || ''}
              onChange={(e) => handleFilterChange('date_from', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="date_to">Date To</Label>
            <Input
              id="date_to"
              type="date"
              value={localFilters.date_to || ''}
              onChange={(e) => handleFilterChange('date_to', e.target.value)}
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