import { Markdown } from '../components/Markdown'
import type { Story } from '../types'

interface StoryReaderProps {
  story: Story
  onBack: () => void
}

export function StoryReader({ story }: StoryReaderProps) {
  return (
    <div className="reader">
      <article className="reader-article prose">
        <Markdown content={story.content} />
      </article>
    </div>
  )
}
