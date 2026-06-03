import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { contentApi, renderingApi } from '@/lib/api'
import { ArrowLeft, Play, CheckCircle, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'

export default function ContentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: brief, isLoading } = useQuery({
    queryKey: ['brief', id],
    queryFn: () => id ? contentApi.getBrief(id) : Promise.reject(),
    enabled: !!id,
  })

  const approveMutation = useMutation({
    mutationFn: (briefId: string) => contentApi.approveBrief(briefId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brief', id] })
      toast.success('Brief approved!')
    },
  })

  const renderMutation = useMutation({
    mutationFn: (briefId: string) => renderingApi.render(briefId, 'male_1', true),
    onSuccess: () => {
      toast.success('Video rendering started!')
      navigate('/queue')
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    )
  }

  if (!brief) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-400">Content brief not found</p>
        <Link to="/queue" className="text-green-500 hover:underline mt-2 block">
          Back to queue
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link
          to="/queue"
          className="flex items-center text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Queue
        </Link>

        <div className="flex items-center space-x-3">
          {brief.status === 'review' && (
            <>
              <button
                onClick={() => approveMutation.mutate(brief.id)}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center"
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                Approve
              </button>
              <button
                onClick={() => renderMutation.mutate(brief.id)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center"
              >
                <Play className="w-4 h-4 mr-2" />
                Generate Video
              </button>
            </>
          )}

          {brief.status === 'generated' && (
            <button
              onClick={() => renderMutation.mutate(brief.id)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center"
            >
              <Play className="w-4 h-4 mr-2" />
              Regenerate Video
            </button>
          )}
        </div>
      </div>

      {/* Brief content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Topic & Status */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-2">Topic</h2>
          <p className="text-xl text-white">{brief.topic}</p>
          
          <div className="mt-4 flex items-center space-x-3">
            <span className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded-full">
              Status: {brief.status}
            </span>
            <span className="text-xs text-slate-400">
              Created {new Date(brief.created_at).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Reel Script */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-2">Reel Script</h2>
          <p className="text-white whitespace-pre-wrap">{brief.reel_script}</p>
        </div>

        {/* Caption */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-2">Caption</h2>
          <p className="text-white whitespace-pre-wrap">{brief.caption}</p>
        </div>

        {/* Hashtags */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-2">Hashtags</h2>
          <div className="flex flex-wrap gap-2">
            {brief.hashtags?.slice(0, 15).map((tag: string, idx: number) => (
              <span
                key={idx}
                className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* Viral Angles */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-2">Viral Angles</h2>
          {brief.viral_angles && brief.viral_angles.length > 0 ? (
            <ul className="space-y-2">
              {brief.viral_angles.slice(0, 5).map((angle: any, idx: number) => (
                <li key={idx} className="text-white text-sm">
                  <span className="text-green-400 font-medium">{angle.type}:</span>{' '}
                  {angle.description}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-400">No viral angles defined</p>
          )}
        </div>

        {/* Visual Direction */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-2">Visual Direction</h2>
          {brief.visual_direction ? (
            <div className="space-y-2 text-sm text-white">
              {Object.entries(brief.visual_direction).map(([key, value]) => (
                <div key={key}>
                  <span className="text-slate-400 capitalize">{key}:</span>{' '}
                  <span className="text-white">{String(value)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-400">No visual direction defined</p>
          )}
        </div>
      </div>
    </div>
  )
}