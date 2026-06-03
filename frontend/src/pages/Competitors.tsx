import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { competitorsApi } from '@/lib/api'
import toast from 'react-hot-toast'
import { Plus, Trash2, Download, Loader2 } from 'lucide-react'
import { getPlatformIcon, formatViralScore } from '@/lib/utils'

export default function Competitors() {
  const [showAddForm, setShowAddForm] = useState(false)
  const [newUsername, setNewUsername] = useState('')
  const [newPlatform, setNewPlatform] = useState('instagram')
  const queryClient = useQueryClient()

  const { data: summary, isLoading } = useQuery({
    queryKey: ['competitors-summary'],
    queryFn: competitorsApi.getSummary,
  })

  const { data: trends } = useQuery({
    queryKey: ['trends'],
    queryFn: () => competitorsApi.getTrends(30),
  })

  const addMutation = useMutation({
    mutationFn: (data: { platform: string; username: string }) =>
      competitorsApi.create(data.platform, data.username, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors-summary'] })
      toast.success('Competitor added!')
      setShowAddForm(false)
      setNewUsername('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => competitorsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors-summary'] })
      toast.success('Competitor removed')
    },
  })

  const scrapeMutation = useMutation({
    mutationFn: (id: string) => competitorsApi.scrape(id, 50, 30),
    onSuccess: () => {
      toast.success('Scraping started in background')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newUsername.trim()) return

    addMutation.mutate({
      platform: newPlatform,
      username: newUsername.trim(),
    })
  }

  return (
    <div className="space-y-6">
      {/* Add competitor */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Competitor Accounts</h2>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Competitor
          </button>
        </div>

        {showAddForm && (
          <form onSubmit={handleSubmit} className="space-y-4 mb-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Platform
                </label>
                <select
                  value={newPlatform}
                  onChange={(e) => setNewPlatform(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  <option value="instagram">Instagram</option>
                  <option value="youtube">YouTube</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  placeholder="e.g., 433, espnfc"
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
            </div>
            <div className="flex space-x-3">
              <button
                type="submit"
                className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
              >
                Add Account
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 bg-slate-600 text-white rounded-lg text-sm font-medium hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Competitors list */}
        {isLoading ? (
          <div className="text-center py-8">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-slate-400" />
          </div>
        ) : summary?.competitors && summary.competitors.length > 0 ? (
          <div className="space-y-3">
            {summary.competitors.map((competitor: any) => (
              <div
                key={competitor.id}
                className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg"
              >
                <div className="flex items-center space-x-4">
                  <span className="text-2xl">{getPlatformIcon(competitor.platform)}</span>
                  <div>
                    <p className="text-white font-medium">@{competitor.username}</p>
                    <p className="text-sm text-slate-400">
                      {formatViralScore(competitor.follower_count)}{' '}
                      {competitor.follower_count ? `${(competitor.follower_count / 1000000).toFixed(1)}M followers` : ''}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <span className="text-sm text-slate-400">
                    {competitor.total_posts_scraped} posts scraped
                  </span>
                  <button
                    onClick={() => scrapeMutation.mutate(competitor.id)}
                    className="p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                    title="Scrape content"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(competitor.id)}
                    className="p-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                    title="Remove competitor"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-400">
            No competitors added yet. Add your first competitor above!
          </div>
        )}
      </div>

      {/* Trends */}
      {trends && trends.trending_topics && trends.trending_topics.length > 0 && (
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">Trending Topics</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {trends.trending_topics.slice(0, 6).map((topic: any, idx: number) => (
              <div
                key={idx}
                className="p-4 bg-slate-700/50 rounded-lg"
              >
                <div className="flex items-center justify-between">
                  <span className="text-white font-medium">{topic.topic}</span>
                  <span className="text-xs text-green-400">
                    Score: {topic.avg_viral_score}
                  </span>
                </div>
                <p className="text-sm text-slate-400 mt-1">
                  {topic.count} posts analyzed
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}