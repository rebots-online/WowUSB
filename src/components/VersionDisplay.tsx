import { useState, useEffect } from 'react'
import { getVersion } from '@tauri-apps/api/app'
import { formatVersion } from '@/lib/utils'

interface VersionDisplayProps {
  position?: 'bottom-right' | 'status-bar' | 'about'
  className?: string
}

export function VersionDisplay({ position = 'bottom-right', className }: VersionDisplayProps) {
  const [version, setVersion] = useState<string>('Loading...')
  const [isError, setIsError] = useState(false)

  useEffect(() => {
    async function loadVersion() {
      try {
        const appVersion = await getVersion()
        setVersion(formatVersion(appVersion))
        setIsError(false)
      } catch (error) {
        console.error('Failed to get version:', error)
        setVersion('Unknown')
        setIsError(true)
      }
    }
    loadVersion()
  }, [])

  const versionText = `WowUSB-DS9 ${version}`

  if (position === 'bottom-right') {
    return (
      <div className={`fixed bottom-4 right-4 text-xs text-gray-500 bg-white/80 backdrop-blur px-2 py-1 rounded border ${isError ? 'border-red-200 text-red-600' : ''} ${className}`}>
        {versionText}
      </div>
    )
  }

  if (position === 'status-bar') {
    return (
      <span className={`text-xs text-gray-600 ${isError ? 'text-red-600' : ''} ${className}`}>
        {versionText}
      </span>
    )
  }

  if (position === 'about') {
    return (
      <div className={`text-center space-y-2 ${className}`}>
        <h3 className="text-lg font-semibold">WowUSB-DS9</h3>
        <p className={`text-2xl font-mono ${isError ? 'text-red-600' : 'text-blue-600'}`}>
          {version}
        </p>
        <p className="text-sm text-gray-600">
          Create bootable Windows USB drives with advanced features
        </p>
        {isError && (
          <p className="text-xs text-red-500 mt-2">
            Version information unavailable
          </p>
        )}
      </div>
    )
  }

  return (
    <span className={isError ? 'text-red-600' : ''}>{versionText}</span>
  )
}