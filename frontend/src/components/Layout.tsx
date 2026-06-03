import { Outlet, Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  List,
  Users,
  BarChart3,
  Settings,
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

  return (
    <div className="min-h-screen bg-slate-900 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-slate-700">
          <img src="/logo.jpeg" alt="Logo" className="w-10 h-10 object-cover rounded-lg" />
          <span className="ml-3 text-lg font-bold text-white">
            World Cup Autoposter
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-2">
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.to

            return (
              <Link
                key={item.name}
                to={item.to}
                className={cn(
                  'flex items-center px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-green-600 text-white'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                )}
              >
                <Icon className="w-5 h-5 mr-3" />
                {item.name}
              </Link>
            )
          })}
        </nav>

        {/* Status indicator */}
        <div className="px-4 py-4 border-t border-slate-700">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>System Status</span>
            <span className="flex items-center">
              <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
              Online
            </span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <header className="h-16 bg-slate-800 border-b border-slate-700 flex items-center px-6">
          <h1 className="text-xl font-semibold text-white">
            {navigation.find(n => n.to === location.pathname)?.name || 'Dashboard'}
          </h1>
        </header>

        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}