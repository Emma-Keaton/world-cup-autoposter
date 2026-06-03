import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsApi } from '@/lib/api'
import { RotateCcw, Check, Key, Bell, Palette, Cpu, Globe } from 'lucide-react'

interface Setting {
  value: any
  type: string
  category: string
  description: string
  is_sensitive: boolean
}

interface SettingsData {
  [key: string]: Setting
}

export default function Settings() {
  const [editedValues, setEditedValues] = useState<Record<string, any>>({})
  const [activeCategory, setActiveCategory] = useState<string>('all')
  const [showSuccess, setShowSuccess] = useState(false)
  const queryClient = useQueryClient()

  const { data: settingsData, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const res = await settingsApi.getAll()
      return res.settings as SettingsData
    },
  })

  const saveMutation = useMutation({
    mutationFn: async (changes: Record<string, any>) => {
      const promises = Object.entries(changes).map(([key, value]) => {
        const setting = settingsData?.[key]
        return settingsApi.update(key, value, setting?.type || 'string')
      })
      return Promise.all(promises)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setEditedValues({})
      setShowSuccess(true)
      setTimeout(() => setShowSuccess(false), 3000)
    },
  })

  const handleSave = () => {
    saveMutation.mutate(editedValues)
  }

  const handleReset = () => {
    setEditedValues({})
  }

  const updateValue = (key: string, value: any) => {
    setEditedValues(prev => ({ ...prev, [key]: value }))
  }

  const isModified = (key: string) => {
    return editedValues[key] !== undefined
  }

  const getCategories = () => {
    if (!settingsData) return []
    const categories = new Set(Object.values(settingsData).map(s => s.category))
    return ['all', ...Array.from(categories)]
  }

  const getFilteredSettings = () => {
    if (!settingsData) return {}
    if (activeCategory === 'all') return settingsData
    
    return Object.fromEntries(
      Object.entries(settingsData).filter(([_, setting]) => setting.category === activeCategory)
    )
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'notifications': return <Bell className="w-4 h-4" />
      case 'publishing': return <Globe className="w-4 h-4" />
      case 'ai': return <Cpu className="w-4 h-4" />
      case 'media': return <Palette className="w-4 h-4" />
      case 'application': return <Key className="w-4 h-4" />
      default: return <Key className="w-4 h-4" />
    }
  }

  const renderInput = (key: string, setting: Setting) => {
    const value = editedValues[key] !== undefined ? editedValues[key] : setting.value

    if (setting.type === 'bool') {
      return (
        <button
          onClick={() => updateValue(key, !value)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            value ? 'bg-blue-600' : 'bg-slate-600'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              value ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      )
    }

    if (setting.is_sensitive) {
      return (
        <input
          type="password"
          value={value || ''}
          onChange={(e) => updateValue(key, e.target.value)}
          className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          placeholder="Enter value..."
        />
      )
    }

    return (
      <input
        type={setting.type === 'int' ? 'number' : 'text'}
        value={value || ''}
        onChange={(e) => updateValue(key, e.target.value)}
        className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
        placeholder="Enter value..."
      />
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    )
  }

  const filteredSettings = getFilteredSettings()
  const hasChanges = Object.keys(editedValues).length > 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Settings</h2>
          <p className="text-slate-400 mt-1">Configure API keys and application preferences</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleReset}
            disabled={!hasChanges}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || saveMutation.isPending}
            className="flex items-center gap-2 px-6 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {saveMutation.isPending ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
            ) : (
              <Check className="w-4 h-4" />
            )}
            Save Changes
          </button>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex gap-2 flex-wrap">
        {getCategories().map(category => (
          <button
            key={category}
            onClick={() => setActiveCategory(category)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeCategory === category
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {getCategoryIcon(category)}
            {category.charAt(0).toUpperCase() + category.slice(1)}
          </button>
        ))}
      </div>

      {/* Settings Grid */}
      <div className="grid gap-6">
        {Object.entries(filteredSettings).map(([key, setting]) => (
          <div
            key={key}
            className={`bg-slate-800 rounded-xl p-6 border transition-colors ${
              isModified(key) ? 'border-blue-500' : 'border-slate-700'
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-white font-medium">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </h3>
                  {isModified(key) && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-600/20 text-blue-400">
                      Modified
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-400 mb-3">{setting.description}</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-1 rounded bg-slate-700 text-slate-400">
                    {setting.type}
                  </span>
                  <span className="text-xs px-2 py-1 rounded bg-slate-700 text-slate-400">
                    {setting.category}
                  </span>
                  {setting.is_sensitive && (
                    <span className="text-xs px-2 py-1 rounded bg-amber-600/20 text-amber-400 flex items-center gap-1">
                      <Key className="w-3 h-3" />
                      Sensitive
                    </span>
                  )}
                </div>
              </div>
              <div className="w-80">
                {renderInput(key, setting)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {Object.keys(filteredSettings).length === 0 && (
        <div className="text-center py-20">
          <p className="text-slate-400">No settings found for this category</p>
        </div>
      )}

      {/* Success Toast */}
      {showSuccess && (
        <div className="fixed bottom-4 right-4 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-3 animate-slide-up">
          <Check className="w-5 h-5" />
          <span>Settings saved successfully!</span>
        </div>
      )}
    </div>
  )
}
