import { useState } from 'react'
import { open } from '@tauri-apps/api/shell'
import { getVersion } from '@tauri-apps/api/app'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { VersionDisplay } from './VersionDisplay'

interface MenuBarProps {
  onNewProject?: () => void
  onOpenProject?: () => void
  onRefreshDevices?: () => void
  onShowAbout?: () => void
}

export function MenuBar({
  onNewProject,
  onOpenProject,
  onRefreshDevices,
  onShowAbout
}: MenuBarProps) {
  const [aboutOpen, setAboutOpen] = useState(false)

  const handleHelpWebsite = async () => {
    await open('https://github.com/rebots-online/WowUSB')
  }

  const handleHelpDocumentation = async () => {
    await open('https://github.com/rebots-online/WowUSB/wiki')
  }

  const handleHelpReportIssue = async () => {
    await open('https://github.com/rebots-online/WowUSB/issues')
  }

  const handleAbout = () => {
    setAboutOpen(true)
    onShowAbout?.()
  }

  return (
    <div className="border-b border-gray-200 bg-white">
      <div className="flex items-center space-x-1 px-2 py-1">
        {/* File Menu */}
        <div className="relative group">
          <button className="px-3 py-1 text-sm hover:bg-gray-100 rounded transition-colors">
            File
          </button>
          <div className="absolute left-0 mt-1 w-48 bg-white border border-gray-200 rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
            <button
              onClick={onNewProject}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors"
            >
              New Project
            </button>
            <button
              onClick={onOpenProject}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors"
            >
              Open Project
            </button>
            <div className="border-t border-gray-200 my-1"></div>
            <button className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors">
              Exit
            </button>
          </div>
        </div>

        {/* Edit Menu */}
        <div className="relative group">
          <button className="px-3 py-1 text-sm hover:bg-gray-100 rounded transition-colors">
            Edit
          </button>
          <div className="absolute left-0 mt-1 w-48 bg-white border border-gray-200 rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
            <button className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors">
              Undo
            </button>
            <button className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors">
              Redo
            </button>
            <div className="border-t border-gray-200 my-1"></div>
            <button className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors">
              Preferences
            </button>
          </div>
        </div>

        {/* View Menu */}
        <div className="relative group">
          <button className="px-3 py-1 text-sm hover:bg-gray-100 rounded transition-colors">
            View
          </button>
          <div className="absolute left-0 mt-1 w-48 bg-white border border-gray-200 rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
            <button
              onClick={onRefreshDevices}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors"
            >
              Refresh Devices
            </button>
            <div className="border-t border-gray-200 my-1"></div>
            <button className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors">
              Toggle Sidebar
            </button>
            <button className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors">
              Full Screen
            </button>
          </div>
        </div>

        {/* Help Menu */}
        <div className="relative group">
          <button className="px-3 py-1 text-sm hover:bg-gray-100 rounded transition-colors">
            Help
          </button>
          <div className="absolute left-0 mt-1 w-48 bg-white border border-gray-200 rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
            <button
              onClick={handleHelpDocumentation}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors"
            >
              Documentation
            </button>
            <button
              onClick={handleHelpWebsite}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors"
            >
              Website
            </button>
            <div className="border-t border-gray-200 my-1"></div>
            <button
              onClick={handleHelpReportIssue}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors"
            >
              Report Issue
            </button>
            <button
              onClick={handleAbout}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors"
            >
              About WowUSB-DS9
            </button>
          </div>
        </div>

        {/* Spacer */}
        <div className="flex-1"></div>

        {/* Version in status bar */}
        <VersionDisplay position="status-bar" className="text-xs mr-2" />
      </div>

      {/* About Dialog */}
      <Dialog open={aboutOpen} onOpenChange={setAboutOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>About WowUSB-DS9</DialogTitle>
          </DialogHeader>
          <VersionDisplay position="about" />
          <div className="mt-4 space-y-2">
            <p className="text-sm text-gray-600">
              <strong>License:</strong> GPL-3.0
            </p>
            <p className="text-sm text-gray-600">
              <strong>Author:</strong> Robin L. M. Cheung, MBA
            </p>
            <p className="text-sm text-gray-600">
              <strong>Website:</strong>{' '}
              <button
                onClick={handleHelpWebsite}
                className="text-blue-600 hover:underline ml-1"
              >
                github.com/rebots-online/WowUSB
              </button>
            </p>
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-xs text-yellow-800">
                <strong>⚠️ Important:</strong> Always verify the version number before use.
                Higher build numbers indicate more recent versions.
              </p>
            </div>
          </div>
          <div className="flex justify-end mt-6">
            <Button onClick={() => setAboutOpen(false)}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}