import { useQuery } from '@tanstack/react-query'
import { healthApi, contentApi, analyticsApi, competitorsApi } from '@/lib/api'
import { TrendingUp, Users, Video, FileText, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatNumber } from '@/lib/utils'

export default function Dashboard() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: healthApi.status,
    refetchInterval: 30000,
  })

  const { data: queue } = useQuery({
    queryKey: ['queue'],
    queryFn: contentApi.getQueue,
    refetchInterval: 10000,
  })

  const { data: analytics } = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: () => analyticsApi.getOverview(30),
  })

  const { data: competitors } = useQuery({
    queryKey: ['competitors-summary'],
    queryFn: competitorsApi.getSummary,
  })

  const stats = [
    {
      name: 'Content Briefs',
      value: queue?.total || 0,
      icon: FileText,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
    },
    {
      name: 'Total Views',
      value: formatNumber(analytics?.total_views || 0),
      icon: TrendingUp,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
    },
    {
      name: 'Competitors',
      value: competitors?.total || 0,
      icon: Users,
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
    },
    {
      name: 'Videos Generated',
      value: formatNumber(health?.database?.generated_videos || 0),
      icon: Video,
      color: 'text-yellow-500',
      bgColor: 'bg-yellow-500/10',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <div
              key={stat.name}
              className="bg-slate-800 rounded-xl p-6 border border-slate-700"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">{stat.name}</p>
                  <p className="text-2xl font-bold text-white mt-1">
                    {healthLoading ? '...' : stat.value}
                  </p>
                </div>
                <div className={`${stat.bgColor} p-3 rounded-lg`}>
                  <Icon className={`w-6 h-6 ${stat.color}`} />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Quick actions */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/queue"
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center"
          >
            <Zap className="w-4 h-4 mr-2" />
            Generate Content
          </Link>
          <Link
            to="/competitors"
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Manage Competitors
          </Link>
          <Link
            to="/analytics"
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            View Analytics
          </Link>
        </div>
      </div>

      {/* System status */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">System Status</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <StatusItem
            label="Database"
            status={health?.database?.status === 'connected' ? 'Connected' : 'Disconnected'}
            active={health?.database?.status === 'connected'}
          />
          <StatusItem
            label="NVIDIA API"
            status={health?.configuration?.nvidia_api ? 'Configured' : 'Not Configured'}
            active={health?.configuration?.nvidia_api}
          />
          <StatusItem
            label="Pexels API"
            status={health?.configuration?.pexels_api ? 'Configured' : 'Not Configured'}
            active={health?.configuration?.pexels_api}
          />
          <StatusItem
            label="Pixabay API"
            status={health?.configuration?.pixabay_api ? 'Configured' : 'Not Configured'}
            active={health?.configuration?.pixabay_api}
          />
          <StatusItem
            label="Meta API"
            status={health?.configuration?.meta_api ? 'Configured' : 'Not Configured'}
            active={health?.configuration?.meta_api}
          />
        </div>
      </div>

      {/* Pending review */}
      {queue?.pending_review && queue.pending_review.length > 0 && (
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">Pending Review</h2>
          <div className="space-y-2">
            {queue.pending_review.slice(0, 5).map((item: any) => (
              <Link
                key={item.id}
                to={`/content/${item.id}`}
                className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition-colors"
              >
                <div>
                  <p className="text-white font-medium">{item.topic}</p>
                  <p className="text-xs text-slate-400">
                    Created {new Date(item.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="px-2 py-1 bg-yellow-500/20 text-yellow-500 text-xs rounded-full">
                  Review
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatusItem({ label, status, active }: { label: string; status: string; active: boolean }) {
  return (
    <div className="flex items-center space-x-2">
      <span className={`w-2 h-2 rounded-full ${active ? 'bg-green-500' : 'bg-red-500'}`} />
      <div>
        <p className="text-xs text-slate-400">{label}</p>
        <p className={`text-sm font-medium ${active ? 'text-green-500' : 'text-red-500'}`}>
          {status}
        </p>
      </div>
    </div>
  )
}