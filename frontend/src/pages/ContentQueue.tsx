import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { contentApi } from '@/lib/api'
import toast from 'react-hot-toast'
import { Play, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn, formatDate, getStatusColor } from '@/lib/utils'

export default function ContentQueue() {
  const [topic, setTopic] = useState('')
  const [autoApprove, setAutoApprove] = useState(false)
  const queryClient = useQueryClient()

  const { data: queue, isLoading } = useQuery({
    queryKey: ['queue'],
    queryFn: contentApi.getQueue,
    refetchInterval: 10000,
  })

  const { data: briefs } = useQuery({
    queryKey: ['briefs'],
    queryFn: () => contentApi.getBriefs(),
  })

  const generateMutation = useMutation({
    mutationFn: (data: { topic: string; auto_approve: boolean }) =>
      contentApi.generate(data.topic, data.auto_approve, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      queryClient.invalidateQueries({ queryKey: ['briefs'] })
      toast.success('Content generated successfully!')
      setTopic('')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to generate content')
    },
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => contentApi.approveBrief(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      toast.success('Brief approved!')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      contentApi.rejectBrief(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      toast.success('Brief rejected')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!topic.trim()) return

    generateMutation.mutate({
      topic: topic.trim(),
      auto_approve: autoApprove,
    })
  }

  return (
    <div className="space-y-6">
      {/* Generate form */}
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">Generate New Content</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="topic" className="block text-sm font-medium text-slate-300 mb-2">
              Football Topic
            </label>
            <input
              type="text"
              id="topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Mbappe transfer to Real Madrid, World Cup 2026 predictions..."
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div className="flex items-center space-x-3">
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={autoApprove}
                onChange={(e) => setAutoApprove(e.target.checked)}
                className="sr-only"
              />
              <div
                className={cn(
                  'w-10 h-6 rounded-full transition-colors',
                  autoApprove ? 'bg-green-600' : 'bg-slate-600'
                )}
              >
                <div
                  className={cn(
                    'w-4 h-4 bg-white rounded-full mt-1 transition-transform',
                    autoApprove ? 'translate-x-5 ml-1' : 'translate-x-1'
                  )}
                />
              </div>
              <span className="ml-2 text-sm text-slate-300">Auto-approve (skip review)</span>
            </label>

            <button
              type="submit"
              disabled={generateMutation.isPending || !topic.trim()}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white rounded-lg text-sm font-medium transition-colors flex items-center"
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Generate
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Queue status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <QueueStatCard
          title="Total Briefs"
          value={queue?.total || 0}
          icon={Clock}
          color="text-blue-500"
        />
        <QueueStatCard
          title="Pending Review"
          value={queue?.by_status?.review || 0}
          icon={Clock}
          color="text-yellow-500"
        />
        <QueueStatCard
          title="Ready for Production"
          value={queue?.by_status?.generated || 0}
          icon={CheckCircle}
          color="text-green-500"
        />
      </div>

      {/* Briefs list */}
      <div className="bg-slate-800 rounded-xl border border-slate-700">
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">Content Briefs</h2>
        </div>

        {isLoading ? (
          <div className="p-6 text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-slate-400" />
          </div>
        ) : briefs?.briefs && briefs.briefs.length > 0 ? (
          <div className="divide-y divide-slate-700">
            {briefs.briefs.map((brief: any) => (
              <div
                key={brief.id}
                className="p-4 hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <Link
                    to={`/content/${brief.id}`}
                    className="flex-1"
                  >
                    <h3 className="text-white font-medium">{brief.topic}</h3>
                    <p className="text-sm text-slate-400 mt-1">
                      Created {formatDate(brief.created_at)}
                    </p>
                  </Link>

                  <div className="flex items-center space-x-3">
                    <span
                      className={cn(
                        'px-2 py-1 rounded-full text-xs font-medium',
                        getStatusColor(brief.status),
                        'text-white'
                      )}
                    >
                      {brief.status}
                    </span>

                    {brief.status === 'review' && (
                      <div className="flex space-x-2">
                        <button
                          onClick={() => approveMutation.mutate(brief.id)}
                          className="p-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                          title="Approve"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => rejectMutation.mutate({ id: brief.id })}
                          className="p-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                          title="Reject"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 text-center text-slate-400">
            No content briefs yet. Generate your first content above!
          </div>
        )}
      </div>
    </div>
  )
}

function QueueStatCard({ title, value, icon: Icon, color }: any) {
  return (
    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
        </div>
        <div className="bg-slate-700 p-3 rounded-lg">
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
      </div>
    </div>
  )
}