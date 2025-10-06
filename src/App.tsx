import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import { listen } from '@tauri-apps/api/event'
import { open } from '@tauri-apps/api/dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { MenuBar } from '@/components/MenuBar'
import { VersionDisplay } from '@/components/VersionDisplay'
import { SplashScreen } from '@/components/SplashScreen'
import { DeviceCard } from '@/components/DeviceCard'
import { formatBytes, validateDevicePath, validateIsoPath } from '@/lib/utils'

interface Device {
  name: string
  size: string
  model: string
  filesystem?: string
  mountpoint?: string
  is_removable: boolean
  is_usb: boolean
}

interface CreateConfig {
  target_os: string
  filesystem: string
  enable_persistence: boolean
  enable_multiboot: bool
  wintogo_enabled: boolean
  drive_label: string
}

interface ProgressEvent {
  progress: number
  message: string
  stage: string
  timestamp: string
}

export default function App() {
  const [showSplash, setShowSplash] = useState(true)
  const [devices, setDevices] = useState<Device[]>([])
  const [selectedDevice, setSelectedDevice] = useState<string>('')
  const [sourceFile, setSourceFile] = useState<string>('')
  const [progress, setProgress] = useState<ProgressEvent | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [targetOS, setTargetOS] = useState<'linux' | 'windows'>('windows')
  const [selectedFilesystem, setSelectedFilesystem] = useState<string>('auto')
  const [enableWinToGo, setEnableWinToGo] = useState(false)
  const [enableMultiboot, setEnableMultiboot] = useState(false)
  const [driveLabel, setDriveLabel] = useState('Windows USB')
  const [error, setError] = useState<string>('')
  const [availableFilesystems, setAvailableFilesystems] = useState<string[]>([])
  const [verificationResults, setVerificationResults] = useState<Record<string, boolean>>({})
  const [isVerifying, setIsVerifying] = useState<string>('')

  useEffect(() => {
    // Listen for progress updates
    const unlisten = listen<ProgressEvent>('progress', (event) => {
      setProgress(event.payload)
    })

    return () => {
      unlisten.then(f => f())
    }
  }, [])

  useEffect(() => {
    if (!showSplash) {
      refreshDevices()
      getFilesystemInfo()
    }
  }, [showSplash])

  const handleSplashComplete = () => {
    setShowSplash(false)
  }

  const handleNewProject = () => {
    // Reset form
    setSelectedDevice('')
    setSourceFile('')
    setProgress(null)
    setIsCreating(false)
    setError('')
    setVerificationResults({})
  }

  const handleOpenProject = async () => {
    try {
      const selected = await open({
        multiple: false,
        filters: [{
          name: 'ISO Files',
          extensions: ['iso']
        }]
      })
      if (selected && !Array.isArray(selected)) {
        setSourceFile(selected.path)
      }
    } catch (err) {
      console.error('Failed to open file dialog:', err)
    }
  }

  const handleRefreshDevices = () => {
    refreshDevices()
  }

  const handleSelectSource = async () => {
    try {
      const selected = await open({
        multiple: false,
        filters: [{
          name: 'ISO Files',
          extensions: ['iso']
        }]
      })
      if (selected && !Array.isArray(selected)) {
        setSourceFile(selected.path)
        setError('')
      }
    } catch (err) {
      console.error('Failed to open file dialog:', err)
      setError('Failed to select ISO file')
    }
  }

  const refreshDevices = async () => {
    try {
      const devices = await invoke<Device[]>('list_devices')
      setDevices(devices)
      setError('')
    } catch (err) {
      console.error('Failed to list devices:', err)
      setError('Failed to list devices')
    }
  }

  const getFilesystemInfo = async () => {
    try {
      const filesystems = await invoke<string[]>('get_filesystem_info')
      setAvailableFilesystems(filesystems)
    } catch (err) {
      console.error('Failed to get filesystem info:', err)
    }
  }

  const handleVerifyDevice = async (device: string) => {
    setIsVerifying(device)
    try {
      const isValid = await invoke<boolean>('verify_device', { device })
      setVerificationResults(prev => ({ ...prev, [device]: isValid }))
    } catch (err) {
      console.error('Failed to verify device:', err)
      setVerificationResults(prev => ({ ...prev, [device]: false }))
    } finally {
      setIsVerifying('')
    }
  }

  const handleDeviceSelect = (deviceName: string) => {
    if (!verificationResults[deviceName]) {
      // Auto-verify if not verified yet
      handleVerifyDevice(deviceName)
    }
    setSelectedDevice(deviceName)
  }

  const createBootableUSB = async () => {
    if (!sourceFile || !selectedDevice) {
      setError('Please select both a source ISO and target device')
      return
    }

    // Validate inputs
    if (!validateIsoPath(sourceFile)) {
      setError('Invalid ISO file path')
      return
    }

    if (!validateDevicePath(selectedDevice)) {
      setError('Invalid device path')
      return
    }

    const config: CreateConfig = {
      target_os: targetOS,
      filesystem: selectedFilesystem === 'auto' ? 'auto' : selectedFilesystem,
      enable_persistence: false,
      enable_multiboot: enableMultiboot,
      wintogo_enabled: enableWinToGo,
      drive_label
    }

    setIsCreating(true)
    setError('')
    setProgress(null)

    try {
      const result = await invoke<string>('create_bootable_usb', {
        sourcePath: sourceFile,
        targetDevice: selectedDevice,
        config
      })

      setProgress({
        progress: 100,
        message: result,
        stage: 'Completed',
        timestamp: new Date().toISOString()
      })

      // Show success message
      setTimeout(() => {
        alert('Bootable USB created successfully!')
      }, 500)
    } catch (err) {
      console.error('Failed to create bootable USB:', err)
      setError('Failed to create bootable USB: ' + (err as Error).message)
    } finally {
      setIsCreating(false)
    }
  }

  const handleCancelOperation = async () => {
    try {
      await invoke('cancel_operation')
      setIsCreating(false)
      setProgress(null)
      setError('Operation cancelled')
    } catch (err) {
      console.error('Failed to cancel operation:', err)
    }
  }

  if (showSplash) {
    return <SplashScreen onComplete={handleSplashComplete} />
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Menu Bar */}
      <MenuBar
        onNewProject={handleNewProject}
        onOpenProject={handleOpenProject}
        onRefreshDevices={handleRefreshDevices}
        onShowAbout={handleNewProject}
      />

      {/* Main Content */}
      <div className="flex-1 container mx-auto p-6 max-w-4xl">
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">W3</span>
              </div>
              WowUSB-DS9 - Modern Cross-Platform USB Creator
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-800">
                  <strong>Error:</strong> {error}
                </p>
              </div>
            )}

            {/* OS Selection */}
            <Tabs value={targetOS} onValueChange={(v) => setTargetOS(v as 'linux' | 'windows')}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="windows">Windows from Linux</TabsTrigger>
                <TabsTrigger value="linux">Linux from Windows</TabsTrigger>
              </TabsList>

              <TabsContent value="windows" className="space-y-4">
                <div className="grid gap-4">
                  <div>
                    <label className="text-sm font-medium">Windows ISO File</label>
                    <div className="flex gap-2 mt-1">
                      <input
                        type="text"
                        value={sourceFile}
                        onChange={(e) => setSourceFile(e.target.value)}
                        placeholder="Select Windows ISO file..."
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        readOnly
                      />
                      <Button onClick={handleSelectSource} variant="outline">
                        Browse
                      </Button>
                    </div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="linux" className="space-y-4">
                <div className="grid gap-4">
                  <div>
                    <label className="text-sm font-medium">Linux ISO File</label>
                    <div className="flex gap-2 mt-1">
                      <input
                        type="text"
                        value={sourceFile}
                        onChange={(e) => setSourceFile(e.target.value)}
                        placeholder="Select Linux ISO file..."
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        readOnly
                      />
                      <Button onClick={handleSelectSource} variant="outline">
                        Browse
                      </Button>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            {/* Device Selection */}
            <div>
              <label className="text-sm font-medium">Target USB Device</label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                {devices.map((device) => (
                  <DeviceCard
                    key={device.name}
                    device={device}
                    isSelected={selectedDevice === device.name}
                    onSelect={() => handleDeviceSelect(device.name)}
                    onVerify={() => handleVerifyDevice(device.name)}
                    isVerifying={isVerifying === device.name}
                    verificationResult={verificationResults[device.name]}
                  />
                ))}
              </div>

              {devices.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <p>No USB devices found. Please connect a USB device and refresh.</p>
                  <Button onClick={handleRefreshDevices} variant="outline" className="mt-4">
                    Refresh Devices
                  </Button>
                </div>
              )}
            </div>

            {/* Configuration Options */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">Filesystem</label>
                  <Select value={selectedFilesystem} onValueChange={setSelectedFilesystem}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Select filesystem" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">Auto (Recommended)</SelectItem>
                      {availableFilesystems.map((fs) => (
                        <SelectItem key={fs} value={fs}>
                          {fs.toUpperCase()}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium">Drive Label</label>
                  <input
                    type="text"
                    value={driveLabel}
                    onChange={(e) => setDriveLabel(e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="wintogo"
                    checked={enableWinToGo}
                    onCheckedChange={setEnableWinToGo}
                  />
                  <label htmlFor="wintogo" className="text-sm font-medium">
                    Windows-To-Go
                  </label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="multiboot"
                    checked={enableMultiboot}
                    onCheckedChange={setEnableMultiboot}
                  />
                  <label htmlFor="multiboot" className="text-sm font-medium">
                    Multi-boot Mode
                  </label>
                </div>
              </div>
            </div>

            {/* Progress Display */}
            {progress && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>{progress.message}</span>
                  <span>{progress.progress}%</span>
                </div>
                <Progress value={progress.progress} className="h-2" />
                <p className="text-xs text-muted-foreground">
                  Stage: {progress.stage}
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={handleRefreshDevices}
                disabled={isCreating}
              >
                Refresh Devices
              </Button>

              {isCreating && (
                <Button
                  variant="outline"
                  onClick={handleCancelOperation}
                >
                  Cancel
                </Button>
              )}

              <Button
                onClick={createBootableUSB}
                disabled={!sourceFile || !selectedDevice || isCreating}
              >
                {isCreating ? 'Creating...' : 'Start Creation'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Version Display - Bottom Right Corner */}
      <VersionDisplay position="bottom-right" />
    </div>
  )
}