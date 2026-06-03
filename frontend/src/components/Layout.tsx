import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  List,
  Users,
  BarChart3,
  Settings,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', to: '/', icon: LayoutDashboard },
  { name: 'Content Queue', to: '/queue', icon: List },
  { name: 'Competitors', to: '/competitors', icon: Users },
  { name: 'Analytics', to: '/analytics', icon: BarChart3 },
  { name: 'Settings', to: '/settings', icon: Settings },
]

export default function Layout() {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const currentPage = navigation.find(n => n.to === location.pathname)?.name || 'Dashboard'

  return (
    <div className="min-h-screen bg-slate-900 flex overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar - fixed position, overlays content */}
      <aside className={cn(
        "fixed top-0 left-0 h-full bg-slate-800 border-r border-slate-700 flex flex-col transition-all duration-300 z-50 shadow-xl",
        sidebarCollapsed ? "w-16" : "w-64",
        sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-700 flex-shrink-0">
          {!sidebarCollapsed && (
            <div className="flex items-center flex-1 min-w-0">
              <img src="/logo.jpeg" alt="Logo" className="w-8 h-8 object-cover rounded-lg flex-shrink-0" />
              <span className="ml-3 text-sm font-bold text-white whitespace-nowrap truncate">
                World Cup Autoposter
              </span>
            </div>
          )}
          {sidebarCollapsed && (
            <img src="/logo.jpeg" alt="Logo" className="w-8 h-8 object-cover rounded-lg mx-auto" />
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-2 rounded-lg hover:bg-slate-700 text-slate-400 hidden lg:flex items-center justify-center ml-2"
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-2 rounded-lg hover:bg-slate-700 text-slate-400 lg:hidden"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation - scrolls independently */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.to

            return (
              <Link
                key={item.name}
                to={item.to}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  'flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  sidebarCollapsed ? 'justify-center' : '',
                  isActive
                    ? 'bg-green-600 text-white'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                )}
              >
                <Icon className={cn("w-5 h-5 flex-shrink-0", sidebarCollapsed ? '' : 'mr-3')} />
                {!sidebarCollapsed && <span className="truncate">{item.name}</span>}
              </Link>
            )
          })}
        </nav>

        {/* Status indicator - fixed at bottom */}
        <div className="px-3 py-4 border-t border-slate-700 flex-shrink-0">
          <div className={cn("flex items-center text-xs text-slate-400", sidebarCollapsed ? "justify-center" : "")}>
            <span className="flex items-center">
              <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse flex-shrink-0"></span>
              {!sidebarCollapsed && "Online"}
            </span>
          </div>
        </div>
      </aside>

      {/* Main content - full width */}
      <main className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Header - full width, centered title */}
        <header className="h-16 bg-slate-800 border-b border-slate-700 flex items-center justify-center px-4 lg:px-6 flex-shrink-0 w-full">
          <div className="flex items-center gap-3 lg:hidden absolute left-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-slate-700 text-slate-400"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>
          <h1 className="text-lg lg:text-xl font-semibold text-white text-center">
            {currentPage}
          </h1>
        </header>

        {/* Page content - scrolls independently */}
        <div className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}