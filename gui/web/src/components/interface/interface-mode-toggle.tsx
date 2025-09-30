'use client'

import { Monitor, MessageCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface InterfaceModeToggleProps {
  mode: 'gui' | 'ai'
  onModeChange: (mode: 'gui' | 'ai') => void
  className?: string
}

export function InterfaceModeToggle({ 
  mode, 
  onModeChange, 
  className 
}: InterfaceModeToggleProps) {
  return (
    <div className={cn('flex items-center space-x-2', className)}>
      <span className="text-sm font-medium text-muted-foreground">Interface:</span>
      <div className="flex rounded-lg border p-1">
        <Button
          variant={mode === 'gui' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => onModeChange('gui')}
          className="flex items-center space-x-2"
        >
          <Monitor className="h-4 w-4" />
          <span>GUI</span>
        </Button>
        <Button
          variant={mode === 'ai' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => onModeChange('ai')}
          className="flex items-center space-x-2"
        >
          <MessageCircle className="h-4 w-4" />
          <span>AI Chat</span>
        </Button>
      </div>
    </div>
  )
}