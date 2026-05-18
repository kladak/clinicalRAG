import { useState } from 'react'

import { api } from '../api/client.js'
import ResponseCard from './ResponseCard.jsx'
import SourceCitations from './SourceCitations.jsx'

const examples = [
  'What are first-line treatments for HFrEF?',
  'What are the diagnostic criteria for sepsis?',
  'What SGLT2 inhibitors are recommended for heart failure?',
  'How should atrial fibrillation stroke risk be assessed?',
  'What anticoagulants are on the WHO Essential Medicines List?',
]

export default function QueryInterface({ collection }) {
  const [query, setQuery] = useState(examples[0])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await api.query({
        query,
        max_sources: 3,
        collection,
      })
      setResult(response)
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to query guidelines.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <form className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm" onSubmit={handleSubmit}>
        <label className="mb-3 block text-sm font-semibold text-slate-700" htmlFor="clinical-query">
          Physician query
        </label>
        <textarea
          id="clinical-query"
          className="min-h-[120px] w-full resize-y rounded-lg border border-slate-300 bg-white px-4 py-3 text-base leading-6 text-slate-900 outline-none transition focus:border-teal focus:ring-2 focus:ring-teal/20"
          placeholder="Ask a clinical question..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />

        <div className="mt-4 flex flex-wrap gap-2">
          {examples.map((example) => (
            <button
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs font-medium text-slate-700 transition hover:border-teal/50 hover:bg-teal/10 hover:text-navy"
              key={example}
              type="button"
              onClick={() => setQuery(example)}
            >
              {example}
            </button>
          ))}
        </div>

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-xs text-slate-500">Collection: {collection}</p>
          <button
            className="inline-flex min-h-[42px] items-center justify-center gap-2 rounded-md bg-teal px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#08998d] disabled:cursor-not-allowed disabled:bg-slate-300"
            type="submit"
            disabled={loading || query.trim().length < 5}
          >
            {loading ? <span className="spinner" aria-hidden="true" /> : null}
            {loading ? 'Querying' : 'Query Guidelines'}
          </button>
        </div>

        {error ? (
          <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}
      </form>

      {result ? <ResponseCard result={result} /> : null}
      {result?.sources?.length ? <SourceCitations sources={result.sources} /> : null}
    </div>
  )
}
