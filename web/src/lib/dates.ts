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

/** Parse a YYYY-MM-DD[THH:...] string as a local-time Date (no UTC shift). */
export function parseLocalDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split('T')[0].split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** Format a Date as YYYY-MM-DD in local time. */
export function toLocalDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Monday-Sunday week bounds (YYYY-MM-DD, local time) for the week containing `ref`. */
export function weekBounds(ref: Date = new Date()): { start: string; end: string } {
  const d = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate())
  // Monday = 0 .. Sunday = 6
  const dayIdx = (d.getDay() + 6) % 7
  const monday = new Date(d)
  monday.setDate(d.getDate() - dayIdx)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return { start: toLocalDateStr(monday), end: toLocalDateStr(sunday) }
}

/** Human-friendly "Apr 13 – Apr 19" style label for a period. */
export function weekRangeLabel(start: string, end: string): string {
  const s = parseLocalDate(start)
  const e = parseLocalDate(end)
  const sameMonth = s.getMonth() === e.getMonth() && s.getFullYear() === e.getFullYear()
  const startStr = s.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  const endStr = sameMonth
    ? e.toLocaleDateString('en-US', { day: 'numeric' })
    : e.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return `${startStr} – ${endStr}`
}
