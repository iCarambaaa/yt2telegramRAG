'use client'

import { useState, useCallback } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/ui/loading-spinner'

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

interface DatabaseExportProps {
  filters: DatabaseFilters
}

type ExportFormat = 'csv' | 'json'
type ExportTable = 'videos' | 'channels' | 'statistics'

export function DatabaseExport({ filters }: DatabaseExportProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('csv')
  const [selectedTable, setSelectedTable] = useState<ExportTable>('videos')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastExport, setLastExport] = useState<{
    filename: string
    recordCount: number
    timestamp: string
  } | null>(null)

  const exportData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const exportRequest = {
        format: selectedFormat,
        table: selectedTable,
        filters: filters
      }

      const response = await fetch('/api/analytics/database/export', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(exportRequest)
      })

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`)
      }

      const data = await response.json()
      
      // Create and download file
      const blob = new Blob([data.export_content], { type: data.content_type })
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
        recordCount: data.record_count,
        timestamp: data.timestamp
      })

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed')
      console.error('Export error:', err)
    } finally {
      setLoading(false)
    }
  }, [selectedFormat, selectedTable, filters])

  const formatOptions = [
    {
      value: 'csv' as ExportFormat,
      label: 'CSV',
      description: 'Comma-separated values for spreadsheet applications'
    },
    {
      value: 'json' as ExportFormat,
      label: 'JSON',
      description: 'JavaScript Object Notation for programmatic use'
    }
  ]

  const tableOptions = [
    {
      value: 'videos' as ExportTable,
      label: 'Video Records',
      description: 'All video processing records with metadata'
    },
    {
      value: 'channels' as ExportTable,
      label: 'Channel Summary',
      description: 'Channel-level statistics and information'
    },
    {
      value: 'statistics' as ExportTable,
      label: 'Database Statistics',
      description: 'Comprehensive database statistics and metrics'
    }
  ]

  const hasFilters = Object.values(filters).some(value => value !== undefined && value !== '')

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-medium mb-2">Export Database Data</h3>
            <p className="text-sm text-muted-foreground">
              Export database records in various formats. Current filters will be applied to the export.
            </p>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Table Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Data to Export</Label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {tableOptions.map((option) => (
                <Card
                  key={option.value}
                  className={`p-4 cursor-pointer transition-colors ${
                    selectedTable === option.value
                      ? 'bg-blue-50 border-blue-200'
                      : 'hover:bg-gray-50'
                  }`}
                  onClick={() => setSelectedTable(option.value)}
                >
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <input
                        type="radio"
                        checked={selectedTable === option.value}
                        onChange={() => setSelectedTable(option.value)}
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

          {/* Format Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Export Format</Label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
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
              <Label className="text-sm font-medium">Active Filters (will be applied to export)</Label>
              <div className="p-3 bg-blue-50 rounded-md">
                <div className="text-sm space-y-1">
                  {Object.entries(filters).map(([key, value]) => 
                    value !== undefined && value !== '' && (
                      <div key={key} className="flex items-center space-x-2">
                        <span className="font-medium capitalize">
                          {key.replace('_', ' ')}:
                        </span>
                        <span>{value.toString()}</span>
                      </div>
                    )
                  )}
                </div>
              </div>
            </div>
          )}

          {!hasFilters && selectedTable === 'videos' && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-sm text-yellow-800">
                No filters applied. All video records will be exported.
              </p>
            </div>
          )}

          {/* Export Button */}
          <div className="flex items-center space-x-4">
            <Button
              onClick={exportData}
              disabled={loading}
              className="flex items-center space-x-2"
            >
              {loading && <LoadingSpinner size="sm" />}
              <span>{loading ? 'Exporting...' : 'Export Data'}</span>
            </Button>
          </div>

          {/* Last Export Info */}
          {lastExport && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-md">
              <div className="text-sm text-green-800">
                <p className="font-medium">Export completed successfully!</p>
                <div className="mt-1 space-y-1">
                  <p>File: {lastExport.filename}</p>
                  <p>Records: {lastExport.recordCount}</p>
                  <p>Time: {new Date(lastExport.timestamp).toLocaleString()}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Export Information */}
      <Card className="p-6">
        <div className="space-y-4">
          <h4 className="font-medium">Export Information</h4>
          <div className="text-sm text-muted-foreground space-y-3">
            <div>
              <strong>Video Records Export:</strong> Includes all video processing data such as titles, 
              processing times, costs, token usage, and model information.
            </div>
            <div>
              <strong>Channel Summary Export:</strong> Provides aggregated statistics per channel 
              including video counts, total costs, and success rates.
            </div>
            <div>
              <strong>Database Statistics Export:</strong> Comprehensive system-wide metrics including 
              storage usage, performance data, and processing trends.
            </div>
            <div className="pt-2 border-t">
              <strong>File Formats:</strong>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li><strong>CSV:</strong> Best for Excel, Google Sheets, and data analysis tools</li>
                <li><strong>JSON:</strong> Ideal for programmatic processing and API integration</li>
              </ul>
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