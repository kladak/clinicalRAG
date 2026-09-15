import ConfidenceScore from './ConfidenceScore.jsx'

export default function ResponseCard({ result, extractiveMode }) {
  if (!result) return null

  const score = Math.max(0, Math.min(1, Number(result.grounding_score || 0)))
  const scoreLabel = `${Math.round(score * 100)}%`
  const citationCoverage = Math.max(0, Math.min(1, Number(result.citation_coverage || 0)))
  const citations = Array.isArray(result.citations) ? result.citations : []
  const isRefusal = Boolean(result.refusal_reason)
  const warning = extractiveMode
    ? 'Extractive mode: answer assembled from retrieved guideline text.'
    : result.warning

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">
            {isRefusal ? 'Refusal / Guardrail' : 'Clinical Response'}
          </p>
          <p className="mt-1 text-sm text-slate-500">Query ID {result.query_id}</p>
        </div>
        <ConfidenceScore confidence={result.confidence} />
      </div>

      <div className="space-y-5 px-5 py-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-medium text-slate-600">Grounding score</span>
              <span className="font-mono text-slate-500">{scoreLabel}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-md bg-slate-100">
              <div className="h-full bg-teal" style={{ width: scoreLabel }} />
            </div>
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-medium text-slate-600">Citation coverage</span>
              <span className="font-mono text-slate-500">{Math.round(citationCoverage * 100)}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-md bg-slate-100">
              <div
                className="h-full bg-navy"
                style={{ width: `${Math.round(citationCoverage * 100)}%` }}
              />
            </div>
          </div>
        </div>

        {result.refusal_reason ? (
          <div className="rounded-md border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <span className="font-semibold">Refusal code: </span>
            <span className="font-mono text-xs">{result.refusal_reason}</span>
          </div>
        ) : null}

        {warning ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <span className="font-semibold">Grounding notice: </span>
            {warning}
          </div>
        ) : null}

        <div className="font-serif text-[16px] leading-[1.7] text-slate-900 whitespace-pre-wrap">
          {result.answer}
        </div>

        {citations.length ? (
          <details className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3">
            <summary className="cursor-pointer text-sm font-semibold text-slate-700">
              Sentence citations ({citations.filter((c) => c.grounded).length}/{citations.length} grounded)
            </summary>
            <ul className="mt-3 space-y-2 text-sm text-slate-600">
              {citations.map((cite, index) => (
                <li className="border-t border-slate-200 pt-2" key={`${index}-${cite.sentence?.slice(0, 24)}`}>
                  <p className="text-slate-800">{cite.sentence}</p>
                  <p className="mt-1 font-mono text-xs text-slate-500">
                    {cite.grounded
                      ? (cite.source_titles || []).join(' · ') || 'grounded'
                      : 'ungrounded'}
                  </p>
                </li>
              ))}
            </ul>
          </details>
        ) : null}

        <p className="text-xs text-slate-500">Responded in {result.latency_ms}ms</p>
      </div>
    </section>
  )
}
