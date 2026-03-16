import { X, ArrowLeft, Pin, Clock, Tag, Folder } from 'lucide-react'
import { cn } from '../lib/utils'
import { entityColors, entityLabels } from '../lib/colors'
import { relativeTime } from '../lib/dates'
import { Markdown } from './Markdown'
import type { Entity, Knowledge, Session, Story } from '../types'

type DetailItem =
  | { kind: 'entity'; data: Entity }
  | { kind: 'knowledge'; data: Knowledge }
  | { kind: 'session'; data: Session }
  | { kind: 'story'; data: Story }

interface DetailModalProps {
  item: DetailItem | null
  onClose: () => void
  onDismiss?: () => void  // hard close (X), vs onClose which may go back to search
  onTagClick?: (tag: string) => void
  showBack?: boolean
}

export function DetailModal({ item, onClose, onDismiss, onTagClick, showBack = false }: DetailModalProps) {
  const isOpen = item !== null

  return (
    <div
      className={cn('detail-overlay', isOpen && 'open')}
      onClick={onClose}
    >
      <div className="detail-modal" onClick={(e) => e.stopPropagation()}>
        {item && (<>
        <div className="detail-bar">
          {showBack && (
            <button className="detail-close" style={{ marginLeft: 0, marginRight: 4 }} onClick={onClose}>
              <ArrowLeft size={18} />
            </button>
          )}
          <div style={{ flex: 1 }}>
            {item.kind === 'entity' && (
              <HeaderBadge
                label={entityLabels[item.data.type]}
                color={entityColors[item.data.type]}
                pinned={item.data.pinned}
              />
            )}
            {item.kind === 'knowledge' && (
              <HeaderBadge
                label="Knowledge"
                color="var(--knowledge-color)"
                pinned={item.data.pinned}
              />
            )}
            {item.kind === 'session' && (
              <HeaderBadge
                label="Session"
                color="var(--session-color)"
                pinned={false}
              />
            )}
            {item.kind === 'story' && (
              <HeaderBadge
                label={`Story · ${item.data.tier}`}
                color="#A78BFA"
                pinned={false}
              />
            )}
          </div>
          <button className="detail-close" onClick={onDismiss || onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="detail-content">
          {item.kind === 'entity' && <EntityDetail entity={item.data} onTagClick={onTagClick} />}
          {item.kind === 'knowledge' && <KnowledgeDetail article={item.data} onTagClick={onTagClick} />}
          {item.kind === 'session' && <SessionDetail session={item.data} onTagClick={onTagClick} />}
          {item.kind === 'story' && <StoryDetail story={item.data} onTagClick={onTagClick} />}
        </div>
        </>)}
      </div>
    </div>
  )
}

function HeaderBadge({ label, color, pinned }: { label: string; color: string; pinned: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 12px',
        borderRadius: 6,
        fontSize: 12,
        fontWeight: 600,
        textTransform: 'uppercase' as const,
        letterSpacing: '0.3px',
        background: `${color}15`,
        color: color,
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
        {label}
      </span>
      {pinned && (
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          fontSize: 12,
          fontWeight: 500,
          color: 'var(--brand)',
        }}>
          <Pin size={12} /> Pinned
        </span>
      )}
    </div>
  )
}

function MetaRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '10px 0',
      borderBottom: '1px solid var(--border)',
      fontSize: 13,
    }}>
      <span style={{ color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center' }}>
        {icon}
      </span>
      <span style={{ color: 'var(--text-tertiary)', minWidth: 80 }}>{label}</span>
      <span style={{ color: 'var(--text-secondary)', flex: 1 }}>{value}</span>
    </div>
  )
}

function TagList({ tags, onTagClick }: { tags: string[]; onTagClick?: (tag: string) => void }) {
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {tags.map((tag) => (
        <span key={tag} className="tag" onClick={() => onTagClick?.(tag)}>{tag}</span>
      ))}
    </div>
  )
}

function EntityDetail({ entity, onTagClick }: { entity: Entity; onTagClick?: (tag: string) => void }) {
  return (
    <>
      <div style={{ marginBottom: 24 }}>
        <Markdown content={entity.content} />
      </div>

      <div style={{ borderTop: '1px solid var(--border)', paddingTop: 4 }}>
        <MetaRow
          icon={<Clock size={14} />}
          label="Created"
          value={`${relativeTime(entity.created_at)} \u00b7 ${new Date(entity.created_at).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`}
        />
        {entity.updated_at !== entity.created_at && (
          <MetaRow
            icon={<Clock size={14} />}
            label="Updated"
            value={relativeTime(entity.updated_at)}
          />
        )}
        {entity.tags && entity.tags.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 0', fontSize: 13 }}>
            <span style={{ color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', paddingTop: 2 }}>
              <Tag size={14} />
            </span>
            <span style={{ color: 'var(--text-tertiary)', minWidth: 80, paddingTop: 2 }}>Tags</span>
            <TagList onTagClick={onTagClick} tags={entity.tags} />
          </div>
        )}
      </div>
    </>
  )
}

function KnowledgeDetail({ article, onTagClick }: { article: Knowledge; onTagClick?: (tag: string) => void }) {
  return (
    <>
      <div style={{ marginBottom: 24 }}>
        <Markdown content={article.content} />
      </div>

      <div style={{ borderTop: '1px solid var(--border)', paddingTop: 4 }}>
        <MetaRow
          icon={<Clock size={14} />}
          label="Updated"
          value={`${relativeTime(article.updated_at)} \u00b7 ${new Date(article.updated_at).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`}
        />
        {article.tags && article.tags.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 0', fontSize: 13 }}>
            <span style={{ color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', paddingTop: 2 }}>
              <Tag size={14} />
            </span>
            <span style={{ color: 'var(--text-tertiary)', minWidth: 80, paddingTop: 2 }}>Tags</span>
            <TagList onTagClick={onTagClick} tags={article.tags} />
          </div>
        )}
      </div>
    </>
  )
}

function StoryDetail({ story, onTagClick }: { story: Story; onTagClick?: (tag: string) => void }) {
  return (
    <>
      <div style={{
        fontSize: 18,
        fontWeight: 700,
        letterSpacing: '-0.4px',
        color: 'var(--text-primary)',
        marginBottom: 6,
      }}>
        {story.title}
      </div>

      {story.period_start && (
        <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 16 }}>
          {story.period_start}{story.period_end ? ` — ${story.period_end}` : ''}
        </div>
      )}

      <div style={{ marginBottom: 24 }}>
        <Markdown content={story.content} />
      </div>

      <div style={{ borderTop: '1px solid var(--border)', paddingTop: 4 }}>
        <MetaRow
          icon={<Clock size={14} />}
          label="Updated"
          value={`${relativeTime(story.updated_at)} · ${new Date(story.updated_at).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`}
        />
        {story.tags && story.tags.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 0', fontSize: 13 }}>
            <span style={{ color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', paddingTop: 2 }}>
              <Tag size={14} />
            </span>
            <span style={{ color: 'var(--text-tertiary)', minWidth: 80, paddingTop: 2 }}>Tags</span>
            <TagList onTagClick={onTagClick} tags={story.tags} />
          </div>
        )}
      </div>
    </>
  )
}

function SessionDetail({ session, onTagClick }: { session: Session; onTagClick?: (tag: string) => void }) {
  return (
    <>
      {session.what_happened && (
        <div style={{ marginBottom: 24 }}>
          <div style={{
            fontSize: 12,
            fontWeight: 500,
            color: 'var(--text-tertiary)',
            textTransform: 'uppercase' as const,
            letterSpacing: '0.5px',
            marginBottom: 10,
          }}>
            What happened
          </div>
          <Markdown content={session.what_happened} />
        </div>
      )}

      {session.for_next_session && (
        <div style={{ marginBottom: 24 }}>
          <div style={{
            fontSize: 12,
            fontWeight: 500,
            color: 'var(--text-tertiary)',
            textTransform: 'uppercase' as const,
            letterSpacing: '0.5px',
            marginBottom: 10,
          }}>
            For next session
          </div>
          <Markdown content={session.for_next_session} />
        </div>
      )}

      <div style={{ borderTop: '1px solid var(--border)', paddingTop: 4 }}>
        <MetaRow
          icon={<Clock size={14} />}
          label="Created"
          value={`${relativeTime(session.created_at)} \u00b7 ${new Date(session.created_at).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`}
        />
        {session.workspace && (
          <MetaRow
            icon={<Folder size={14} />}
            label="Workspace"
            value={session.workspace}
          />
        )}
        {session.tags && session.tags.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 0', fontSize: 13 }}>
            <span style={{ color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', paddingTop: 2 }}>
              <Tag size={14} />
            </span>
            <span style={{ color: 'var(--text-tertiary)', minWidth: 80, paddingTop: 2 }}>Tags</span>
            <TagList onTagClick={onTagClick} tags={session.tags} />
          </div>
        )}
      </div>
    </>
  )
}
