import { Markdown } from '../components/Markdown'
import type { Story } from '../types'

interface StoryReaderProps {
  story: Story
  onBack: () => void
}

export function StoryReader({ story, onBack }: StoryReaderProps) {
  return (
    <div className="reader">
      <button className="reader-back" onClick={onBack}>
        ← Back
      </button>
      <article className="reader-article prose">
        <Markdown content={story.content} />
      </article>
    </div>
  )
}
