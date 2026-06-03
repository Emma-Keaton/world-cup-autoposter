import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '@/lib/api'
import { TrendingUp, Eye, ThumbsUp, Share2, Loader2 } from 'lucide-react'

export default function Analytics() {
  const { data: overview, isLoading } = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: () => analyticsApi.getOverview(30),
  })

  const { data: feedback } = useQuery({
    queryKey: ['analytics-feedback'],
    queryFn: () => analyticsApi.getFeedback(20),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overview stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Views"
          value={overview?.total_views || 0}
          icon={Eye}
          color="text-blue-500"
        />
        <StatCard
          title="Total Likes"
          value={overview?.total_likes || 0}
          icon={ThumbsUp}
          color="text-green-500"
        />
        <StatCard
          title="Total Shares"
          value={overview?.total_shares || 0}
          icon={Share2}
          color="text-purple-500"
        />
        <StatCard
          title="Avg Viral Score"
          value={overview?.avg_viral_score || 0}
          icon={TrendingUp}
          color="text-yellow-500"
        />
      </div>

      {/* Best performer */}
      {overview?.best_performer && (
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">🏆 Best Performer</h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white font-medium text-lg">
                {overview.best_performer.title}
              </p>
              <p className="text-sm text-slate-400 mt-1">
                {overview.best_performer.views.toLocaleString()} views
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-green-500">
                {overview.best_performer.viral_score}
              </p>
              <p className="text-xs text-slate-400">Viral Score</p>
            </div>
          </div>
        </div>
      )}

      {/* Feedback insights */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">Performance Insights</h2>
        
        {feedback?.feedback && feedback.feedback.length > 0 ? (
          <div className="space-y-3">
            {feedback.feedback.map((item: any, idx: number) => (
              <div
                key={idx}
                className={`p-4 rounded-lg ${
                  item.type === 'success'
                    ? 'bg-green-500/10 border border-green-500/30'
                    : 'bg-yellow-500/10 border border-yellow-500/30'
                }`}
              >
                <p className="font-medium text-white">{item.message}</p>
                {item.examples && (
                  <ul className="mt-2 space-y-1">
                    {item.examples.map((ex: string, i: number) => (
                      <li key={i} className="text-sm text-slate-300">
                        • {ex}
                      </li>
                    ))}
                  </ul>
                )}
                {item.suggestion && (
                  <p className="mt-2 text-sm text-slate-400">{item.suggestion}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-400">
            No performance data available yet. Publish some content to see insights.
          </p>
        )}

        {feedback?.recommendation && (
          <div className="mt-4 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-sm text-blue-300">
              <strong>Recommendation:</strong> {feedback.recommendation}
            </p>
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">30-Day Summary</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryItem label="Videos Analyzed" value={overview?.analyzed_videos || 0} />
          <SummaryItem label="Avg Engagement Rate" value={`${overview?.avg_engagement_rate || 0}%`} />
          <SummaryItem label="Total Content" value={overview?.total_videos || 0} />
          <SummaryItem label="Period" value={`${overview?.period_days || 30} days`} />
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, icon: Icon, color }: any) {
  return (
    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
        </div>
        <div className="bg-slate-700 p-3 rounded-lg">
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
      </div>
    </div>
  )
}

function SummaryItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-4 bg-slate-700/50 rounded-lg">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="text-xl font-bold text-white mt-1">{value}</p>
    </div>
  )
}