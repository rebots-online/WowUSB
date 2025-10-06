import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function formatVersion(version: string): string {
  // Ensure version always starts with 'v'
  if (!version.startsWith('v')) {
    return `v${version}`
  }
  return version
}

export function formatBuildDate(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function validateDevicePath(path: string): boolean {
  // Basic validation for device paths
  if (!path || path.trim() === '') return false

  // Windows device paths
  if (path.startsWith('\\\\.\\PhysicalDrive')) {
    const diskNumber = path.replace('\\\\.\\PhysicalDrive', '')
    return /^\d+$/.test(diskNumber)
  }

  // Unix/Linux device paths
  if (path.startsWith('/dev/')) {
    return /^[a-zA-Z0-9/]+$/.test(path)
  }

  return false
}

export function validateIsoPath(path: string): boolean {
  if (!path || path.trim() === '') return false

  // Check if file has .iso extension
  return path.toLowerCase().endsWith('.iso')
}

export function getDeviceIcon(device: any): string {
  if (device.is_usb) {
    return '🖴'
  } else if (device.is_removable) {
    return '💾'
  } else {
    return '💿'
  }
}

export function getStatusColor(status: 'ready' | 'busy' | 'error' | 'unknown'): string {
  switch (status) {
    case 'ready':
      return 'text-green-600'
    case 'busy':
      return 'text-yellow-600'
    case 'error':
      return 'text-red-600'
    default:
      return 'text-gray-600'
  }
}