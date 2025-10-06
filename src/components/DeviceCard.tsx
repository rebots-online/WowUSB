import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { HardDrive, CheckCircle, AlertCircle } from 'lucide-react'
import { getDeviceIcon, getStatusColor, formatBytes } from '@/lib/utils'

interface Device {
  name: string
  size: string
  model: string
  filesystem?: string
  mountpoint?: string
  is_removable: boolean
  is_usb: boolean
}

interface DeviceCardProps {
  device: Device
  isSelected: boolean
  onSelect: () => void
  onVerify?: () => void
  isVerifying?: boolean
  verificationResult?: boolean
}

export function DeviceCard({
  device,
  isSelected,
  onSelect,
  onVerify,
  isVerifying = false,
  verificationResult
}: DeviceCardProps) {
  const handleSelect = () => {
    if (!device.mountpoint && !isVerifying) {
      onSelect()
    }
  }

  const handleVerify = (e: React.MouseEvent) => {
    e.stopPropagation()
    onVerify?.()
  }

  const isOccupied = device.mountpoint !== null && device.mountpoint !== undefined
  const canSelect = !isOccupied

  return (
    <Card
      className={`
        device-card cursor-pointer transition-all
        ${isSelected ? 'ring-2 ring-blue-500 shadow-lg' : ''}
        ${!canSelect ? 'opacity-60 cursor-not-allowed' : 'hover:shadow-md'}
      `}
      onClick={canSelect ? handleSelect : undefined}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="text-2xl">
              {getDeviceIcon(device)}
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{device.model}</h3>
              <p className="text-sm text-gray-600 font-mono">{device.name}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {device.is_usb && (
              <Badge variant="default" className="bg-blue-100 text-blue-800">
                USB
              </Badge>
            )}
            {device.is_removable && !device.is_usb && (
              <Badge variant="secondary" className="bg-gray-100 text-gray-800">
                Removable
              </Badge>
            )}
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Size:</span>
            <span className="text-sm font-medium">{device.size}</span>
          </div>

          {device.filesystem && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Filesystem:</span>
              <span className="text-sm font-medium">{device.filesystem}</span>
            </div>
          )}

          {isOccupied && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Mount Point:</span>
              <span className="text-sm font-medium text-orange-600">{device.mountpoint}</span>
            </div>
          )}

          {verificationResult !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Status:</span>
              <div className="flex items-center gap-1">
                {verificationResult ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="text-sm font-medium text-green-600">Verified</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-red-500" />
                    <span className="text-sm font-medium text-red-600">Not Verified</span>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-2 mt-4">
          {canSelect ? (
            <Button
              onClick={handleSelect}
              variant={isSelected ? "default" : "outline"}
              className="flex-1"
            >
              {isSelected ? 'Selected' : 'Select'}
            </Button>
          ) : (
            <Button
              disabled
              variant="outline"
              className="flex-1"
            >
              Occupied
            </Button>
          )}

          {onVerify && (
            <Button
              onClick={handleVerify}
              variant="outline"
              size="sm"
              disabled={isVerifying}
              className="flex items-center gap-2"
            >
              {isVerifying ? (
                <>
                  <div className="w-3 h-3 border border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  Verifying...
                </>
              ) : (
                <>
                  <HardDrive className="w-4 h-4" />
                  Verify
                </>
              )}
            </Button>
          )}
        </div>

        {isOccupied && (
          <div className="mt-3 p-2 bg-orange-50 border border-orange-200 rounded text-xs text-orange-800">
            <strong>Warning:</strong> This device is currently mounted. Unmount it before using WowUSB-DS9.
          </div>
        )}
      </CardContent>
    </Card>
  )
}