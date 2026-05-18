import { useState } from 'react'

function typeLabel(value) {
  if (!value) return 'Guideline'
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export default function SourceCitations({ sources = [] }) {
  const [open, setOpen] = useState({})

  if (!sources.length) return null

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase text-slate-500">
          Source Guidelines ({sources.length} sources)
        </h2>
      </div>

      <div className="space-y-3">
        {sources.map((source, index) => {
          const expanded = Boolean(open[index])
          const relevance = `${Math.round(Number(source.relevance_score || 0) * 100)}% relevant`
          const chunkNumber =
            source.chunk_index === null || source.chunk_index === undefined
              ? null
              : Number(source.chunk_index) + 1

          return (
            <article
              key={`${source.document_id}-${source.chunk_index}-${index}`}
              className="rounded-lg border border-slate-200 border-l-4 border-l-teal bg-white p-4 shadow-sm"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 className="font-semibold text-slate-900">{source.title}</h3>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600">
                      {typeLabel(source.document_type)}
                    </span>
                    <span className="font-mono text-xs text-teal">{relevance}</span>
                  </div>
                </div>
                {source.source_url ? (
                  <a
                    className="text-sm font-medium text-teal hover:text-teal/80"
                    href={source.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Source URL
                  </a>
                ) : null}
              </div>

              <p
                className={`mt-4 whitespace-pre-wrap font-mono text-[13px] leading-6 text-slate-700 ${expanded ? '' : 'clamp-3'}`}
              >
                {source.content_excerpt}
              </p>

              <div className="mt-3 flex items-center justify-between gap-3">
                <p className="text-xs text-slate-500">
                  {chunkNumber && source.total_chunks
                    ? `Chunk ${chunkNumber} of ${source.total_chunks}`
                    : 'Retrieved chunk'}
                </p>
                <button
                  className="rounded-md px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100"
                  type="button"
                  onClick={() => setOpen((prev) => ({ ...prev, [index]: !expanded }))}
                >
                  {expanded ? 'Show less' : 'Show more'}
                </button>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
