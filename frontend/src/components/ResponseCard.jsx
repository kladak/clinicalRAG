import ConfidenceScore from './ConfidenceScore.jsx'

export default function ResponseCard({ result }) {
  if (!result) return null

  const score = Math.max(0, Math.min(1, Number(result.grounding_score || 0)))
  const scoreLabel = `${Math.round(score * 100)}%`

  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Clinical Response</p>
          <p className="mt-1 text-sm text-slate-500">Query ID {result.query_id}</p>
        </div>
        <ConfidenceScore confidence={result.confidence} />
      </div>

      <div className="space-y-5 px-5 py-5">
        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-medium text-slate-600">Grounding score</span>
            <span className="font-mono text-slate-500">{scoreLabel}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-md bg-slate-100">
            <div className="h-full bg-teal" style={{ width: scoreLabel }} />
          </div>
        </div>

        {result.warning ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <span className="font-semibold">Grounding notice: </span>
            {result.warning}
          </div>
        ) : null}

        <div className="font-serif text-[16px] leading-[1.7] text-slate-900 whitespace-pre-wrap">
          {result.answer}
        </div>

        <p className="text-xs text-slate-500">Responded in {result.latency_ms}ms</p>
      </div>
    </section>
  )
}
