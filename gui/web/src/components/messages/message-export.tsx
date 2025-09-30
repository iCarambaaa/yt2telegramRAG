'use client'

import { useState, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

interface MessageFilters {
  channel_id?: string
  chat_id?: string
  message_type?: string
  thread_id?: string
  start_date?: string
  end_date?: string
}

interface MessageExportProps {
  filters: MessageFilters
}

type ExportFormat = 'json' | 'csv' | 'txt'

export function MessageExport({ filters }: MessageExportProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('json')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastExport, setLastExport] = useState<{
    filename: string
    messageCount: number
    timestamp: string
  } | null>(null)

  const exportMessages = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        format: selectedFormat,
        ...Object.fromEntries(
          Object.entries(filters).filter(([_, value]) => value)
        )
      })

      const response = await fetch(`/api/messages/export?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`)
      }

      const data = await response.json()
      
      // Create and download file
      const blob = new Blob([data.export_data], { type: data.content_type })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = data.filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      // Update last export info
      setLastExport({
        filename: data.filename,
        messageCount: data.message_count,
        timestamp: data.timestamp
      })

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed')
      console.error('Export error:', err)
    } finally {
      setLoading(false)
    }
  }, [selectedFormat, filters])

  const formatOptions = [
    {
      value: 'json' as ExportFormat,
      label: 'JSON',
      description: 'Structured data with all fields and metadata'
    },
    {
      value: 'csv' as ExportFormat,
      label: 'CSV',
      description: 'Spreadsheet format with core message fields'
    },
    {
      value: 'txt' as ExportFormat,
      label: 'Text',
      description: 'Plain text format for easy reading'
    }
  ]

  const hasFilters = Object.values(filters).some(value => value)

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-medium mb-2">Export Messages</h3>
            <p className="text-sm text-muted-foreground">
              Export messages in various formats. Current filters will be applied to the export.
            </p>
          </div>

          {/* Format Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Export Format</Label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {formatOptions.map((option) => (
                <Card
                  key={option.value}
                  className={`p-4 cursor-pointer transition-colors ${
                    selectedFormat === option.value
                      ? 'bg-blue-50 border-blue-200'
                      : 'hover:bg-gray-50'
                  }`}
                  onClick={() => setSelectedFormat(option.value)}
                >
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <input
                        type="radio"
                        checked={selectedFormat === option.value}
                        onChange={() => setSelectedFormat(option.value)}
                        className="text-blue-600"
                      />
                      <Label className="font-medium">{option.label}</Label>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {option.description}
                    </p>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* Active Filters */}
          {hasFilters && (
            <div className="space-y-2">
              <Label className="text-sm font-medium">Active Filters</Label>
              <div className="p-3 bg-blue-50 rounded-md">
                <div className="text-sm space-y-1">
                  {Object.entries(filters).map(([key, value]) => 
                    value && (
                      <div key={key} className="flex items-center space-x-2">
                        <span className="font-medium capitalize">
                          {key.replace('_', ' ')}:
                        </span>
                        <span>{value}</span>
                      </div>
                    )
                  )}
                </div>
              </div>
            </div>
          )}

          {!hasFilters && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-sm text-yellow-800">
                No filters applied. All messages will be exported.
              </p>
            </div>
          )}

          {/* Export Button */}
          <div className="flex items-center space-x-4">
            <Button
              onClick={exportMessages}
              disabled={loading}
              className="flex items-center space-x-2"
            >
              {loading && <LoadingSpinner size="sm" />}
              <span>{loading ? 'Exporting...' : 'Export Messages'}</span>
            </Button>
          </div>

          {/* Error Display */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">Error: {error}</p>
            </div>
          )}

          {/* Last Export Info */}
          {lastExport && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-md">
              <div className="text-sm text-green-800">
                <p className="font-medium">Export completed successfully!</p>
                <div className="mt-1 space-y-1">
                  <p>File: {lastExport.filename}</p>
                  <p>Messages: {lastExport.messageCount}</p>
                  <p>Time: {new Date(lastExport.timestamp).toLocaleString()}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Export Tips */}
      <Card className="p-6">
        <div className="space-y-4">
          <h4 className="font-medium">Export Tips</h4>
          <div className="text-sm text-muted-foreground space-y-2">
            <div>
              <strong>JSON Format:</strong> Best for programmatic use. Includes all message data, 
              metadata, formatting, and attachments.
            </div>
            <div>
              <strong>CSV Format:</strong> Great for spreadsheet analysis. Includes core message 
              fields in tabular format.
            </div>
            <div>
              <strong>Text Format:</strong> Human-readable format. Good for documentation or 
              simple text processing.
            </div>
            <div className="pt-2 border-t">
              <strong>Note:</strong> Large exports may take some time to process. The file will 
              automatically download when ready.
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}