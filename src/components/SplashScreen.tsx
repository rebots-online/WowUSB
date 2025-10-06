import { useState, useEffect } from 'react'
import { getVersion } from '@tauri-apps/api/app'
import { formatVersion } from '@/lib/utils'

interface SplashScreenProps {
  onComplete: () => void
  minDisplayTime?: number
}

export function SplashScreen({ onComplete, minDisplayTime = 2000 }: SplashScreenProps) {
  const [version, setVersion] = useState<string>('')
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [loadingMessage, setLoadingMessage] = useState('Initializing...')

  useEffect(() => {
    async function initializeApp() {
      try {
        // Get version
        const appVersion = await getVersion()
        setVersion(formatVersion(appVersion))
        setLoadingMessage('Loading components...')

        // Simulate loading progress
        const progressInterval = setInterval(() => {
          setLoadingProgress(prev => {
            const newProgress = prev + Math.random() * 15
            if (newProgress >= 100) {
              clearInterval(progressInterval)
              return 100
            }
            return Math.min(newProgress, 95)
          }

          // Update loading message based on progress
          if (newProgress > 80) {
            setLoadingMessage('Finalizing...')
          } else if (newProgress > 60) {
            setLoadingMessage('Loading user interface...')
          } else if (newProgress > 40) {
            setLoadingMessage('Initializing services...')
          } else if (newProgress > 20) {
            setLoadingMessage('Loading drivers...')
          }
        }, 100)

        // Wait minimum display time
        await new Promise(resolve => setTimeout(resolve, minDisplayTime))

        // Complete loading
        setLoadingProgress(100)
        setLoadingMessage('Ready!')
        clearInterval(progressInterval)

        // Small delay before completing
        setTimeout(() => {
          onComplete()
        }, 300)
      } catch (error) {
        console.error('Failed to initialize app:', error)
        setLoadingMessage('Error loading application')
        setLoadingProgress(0)

        // Still complete after a delay even if there's an error
        setTimeout(() => {
          onComplete()
        }, 1000)
      }
    }

    initializeApp()
  }, [onComplete, minDisplayTime])

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center z-50">
      <div className="text-center space-y-6 max-w-md mx-auto p-8">
        {/* Logo/Icon */}
        <div className="flex justify-center">
          <div className="splash-logo">
            <span className="text-white font-bold text-2xl">W3</span>
          </div>
        </div>

        {/* App Name */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">WowUSB-DS9</h1>
          <p className="text-lg text-gray-600 mt-1">Create Bootable Windows USB Drives</p>
          <p className="text-sm text-gray-500 mt-1">Modern Cross-Platform USB Creator</p>
        </div>

        {/* Version Display */}
        <div className="bg-white/50 backdrop-blur rounded-lg px-4 py-2 border border-gray-200 shadow-sm">
          <p className="text-xl font-mono font-semibold text-blue-600">
            {version || 'Loading...'}
          </p>
        </div>

        {/* Loading Progress */}
        <div className="w-full space-y-2">
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div
              className="progress-bar-animated bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(loadingProgress, 100)}%` }}
            ></div>
          </div>
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-600">
              {loadingMessage}
            </p>
            <p className="text-sm text-gray-500">
              {Math.round(Math.min(loadingProgress, 100))}%
            </p>
          </div>
        </div>

        {/* Warning Text */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <p className="text-xs text-yellow-800 leading-relaxed">
            <strong>⚠️ IMPORTANT:</strong> Always verify the version number before use.
            Higher build numbers indicate more recent versions and may contain important bug fixes.
          </p>
        </div>

        {/* Additional Info */}
        <div className="text-center space-y-1">
          <p className="text-xs text-gray-500">
            Supports Windows from Linux and Linux from Windows
          </p>
          <p className="text-xs text-gray-500">
            Modern interface with comprehensive error handling
          </p>
        </div>
      </div>
    </div>
  )
}