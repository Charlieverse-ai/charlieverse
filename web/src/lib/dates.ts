export function relativeTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const minutes = Math.floor((now.getTime() - d.getTime()) / 60000)

  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  if (hours < 48) return 'Yesterday'

  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function dateGroup(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const dDate = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const nDate = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diff = Math.floor((nDate.getTime() - dDate.getTime()) / (1000 * 60 * 60 * 24))

  if (diff <= 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric' })
}

export function groupByDate<T extends { created_at: string }>(items: T[]): [string, T[]][] {
  const groups = new Map<string, T[]>()
  for (const item of items) {
    const key = dateGroup(item.created_at)
    const group = groups.get(key) || []
    group.push(item)
    groups.set(key, group)
  }
  return Array.from(groups.entries())
}
