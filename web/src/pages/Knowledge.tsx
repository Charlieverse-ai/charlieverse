import { useKnowledge } from '../hooks/use-knowledge'
import { KnowledgeCard } from '../components/KnowledgeCard'
import type { Knowledge } from '../types'

interface KnowledgePageProps {
  onSelect: (article: Knowledge) => void
  onTagClick: (tag: string) => void
}

export function KnowledgePage({ onSelect, onTagClick }: KnowledgePageProps) {
  const { data: articles, isLoading } = useKnowledge()

  return (
    <div>
      {isLoading && (
        <div className="text-sm text-[var(--text-tertiary)] py-8 text-center">Loading...</div>
      )}

      {!isLoading && articles?.length === 0 && (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          <div>No knowledge articles yet</div>
        </div>
      )}

      <div className="k-grid">
        {articles?.map((article) => (
          <KnowledgeCard
            key={article.id}
            article={article}
            onClick={() => onSelect(article)}
            onTagClick={onTagClick}
          />
        ))}
      </div>
    </div>
  )
}
