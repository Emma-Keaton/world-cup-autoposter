import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateString))
}

export function formatNumber(num: number): string {
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`
  }
  return num.toString()
}

export function formatViralScore(score: number | null): string {
  if (!score) return 'N/A'
  if (score >= 10) return '🔥 Viral'
  if (score >= 5) return '📈 Good'
  if (score >= 3) return '📊 Average'
  return '📉 Low'
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    draft: 'bg-gray-500',
    generated: 'bg-blue-500',
    review: 'bg-yellow-500',
    scheduled: 'bg-purple-500',
    published: 'bg-green-500',
    failed: 'bg-red-500',
  }
  return colors[status.toLowerCase()] || 'bg-gray-500'
}

export function getPlatformIcon(platform: string): string {
  if (platform.toLowerCase() === 'instagram') return '📸'
  if (platform.toLowerCase() === 'youtube') return '📺'
  if (platform.toLowerCase() === 'tiktok') return '🎵'
  return '📱'
}