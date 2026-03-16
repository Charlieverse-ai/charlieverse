/** Strip markdown syntax for plain-text previews. */
export function stripMarkdown(text: string): string {
  return text
    .replace(/^#{1,6}\s+/gm, '')        // headings
    .replace(/\*\*(.+?)\*\*/g, '$1')    // bold
    .replace(/\*(.+?)\*/g, '$1')        // italic
    .replace(/__(.+?)__/g, '$1')        // bold alt
    .replace(/_(.+?)_/g, '$1')          // italic alt
    .replace(/`{3}[\s\S]*?`{3}/g, '')   // code blocks
    .replace(/`(.+?)`/g, '$1')          // inline code
    .replace(/^\s*[-*+]\s+/gm, '')      // unordered lists
    .replace(/^\s*\d+\.\s+/gm, '')      // ordered lists
    .replace(/^\s*>\s+/gm, '')          // blockquotes
    .replace(/\[(.+?)\]\(.+?\)/g, '$1') // links
    .replace(/!\[.*?\]\(.+?\)/g, '')    // images
    .replace(/---+/g, '')               // horizontal rules
    .replace(/\n{2,}/g, ' ')            // collapse newlines
    .replace(/\n/g, ' ')
    .trim()
}
