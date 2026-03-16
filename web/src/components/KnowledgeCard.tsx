import { Pin } from 'lucide-react'
import { stripMarkdown } from '../lib/markdown'
import type { Knowledge } from '../types'

interface KnowledgeCardProps {
  article: Knowledge
  onClick: () => void
  onTagClick?: (tag: string) => void
}

export function KnowledgeCard({ article, onClick, onTagClick: _onTagClick }: KnowledgeCardProps) {
  const plain = stripMarkdown(article.content)
  const preview = plain.length > 150 ? plain.slice(0, 150) + '...' : plain

  return (
    <div className="k-card" onClick={onClick}>
      <div className="k-head">
        <div className="k-topic">{article.topic}</div>
        {article.pinned && (
          <span className="k-pin">
            <Pin size={14} />
          </span>
        )}
      </div>
      <div className="k-preview">{preview}</div>
    </div>
  )
}
