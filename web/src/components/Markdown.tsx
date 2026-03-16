import ReactMarkdown from 'react-markdown'

export function Markdown({ content }: { content: string }) {
  return (
    <div className="prose">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}
