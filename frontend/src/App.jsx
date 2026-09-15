import { useEffect, useMemo, useState } from 'react'

import { api } from './api/client.js'
import DocumentIngester from './components/DocumentIngester.jsx'
import QueryInterface from './components/QueryInterface.jsx'

function HealthDot({ ok, llmConfigured }) {
  const llmLabel = llmConfigured ? 'Groq connected' : 'Extractive mode'

  return (
    <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-600">
      <span className="inline-flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${ok ? 'bg-emerald-500' : 'bg-red-500'}`} />
        {ok ? 'API online' : 'API offline'}
      </span>
      {ok ? (
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-teal" />
          {llmLabel}
        </span>
      ) : null}
    </span>
  )
}

function AuditView() {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadAudit() {
      setLoading(true)
      setError('')
      try {
        const response = await api.audit()
        if (!cancelled) setEntries(response.entries || [])
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || 'Unable to load audit log.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadAudit()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="mx-auto w-full max-w-5xl rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-lg font-semibold text-slate-900">Audit Log</h2>
      </div>

      {loading ? <p className="px-5 py-6 text-sm text-slate-500">Loading audit entries...</p> : null}
      {error ? <p className="px-5 py-6 text-sm text-red-600">{error}</p> : null}

      {!loading && !error ? (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-5 py-3 font-semibold">Timestamp</th>
                <th className="px-5 py-3 font-semibold">Query hash</th>
                <th className="px-5 py-3 font-semibold">Collection</th>
                <th className="px-5 py-3 font-semibold">Sources</th>
                <th className="px-5 py-3 font-semibold">Grounding</th>
                <th className="px-5 py-3 font-semibold">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entries.map((entry) => (
                <tr className="text-slate-700" key={entry.query_id || entry.id || entry.timestamp}>
                  <td className="whitespace-nowrap px-5 py-3">
                    {new Date(entry.timestamp).toLocaleString()}
                  </td>
                  <td className="px-5 py-3 font-mono text-xs">{entry.query_hash.slice(0, 18)}...</td>
                  <td className="px-5 py-3 font-mono text-xs">{entry.collection}</td>
                  <td className="px-5 py-3">{entry.sources_retrieved}</td>
                  <td className="px-5 py-3">{Math.round(Number(entry.grounding_score || 0) * 100)}%</td>
                  <td className="px-5 py-3">{entry.latency_ms}ms</td>
                </tr>
              ))}
              {!entries.length ? (
                <tr>
                  <td className="px-5 py-6 text-sm text-slate-500" colSpan="6">
                    No audit entries yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}

export default function App() {
  const [activeView, setActiveView] = useState('query')
  const [health, setHealth] = useState(null)
  const [healthOk, setHealthOk] = useState(false)
  const [selectedCollection, setSelectedCollection] = useState('clinical_guidelines')
  const [refreshKey, setRefreshKey] = useState(0)
  const [ingestOpen, setIngestOpen] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadHealth() {
      try {
        const response = await api.health()
        if (cancelled) return
        setHealth(response)
        setHealthOk(true)
        if (response.collections?.[0]?.name && !selectedCollection) {
          setSelectedCollection(response.collections[0].name)
        }
      } catch {
        if (!cancelled) {
          setHealthOk(false)
          setHealth(null)
        }
      }
    }

    loadHealth()
    const interval = window.setInterval(loadHealth, 30000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [refreshKey, selectedCollection])

  const collections = health?.collections || []
  const totalDocuments = useMemo(
    () => collections.reduce((sum, item) => sum + Number(item.document_count || 0), 0),
    [collections],
  )

  return (
    <div className="min-h-screen bg-cream text-navy lg:flex">
      <aside className="flex w-full flex-col bg-navy px-4 py-5 text-white lg:fixed lg:inset-y-0 lg:w-[240px]">
        <div className="mb-7">
          <p className="font-mono text-xl font-semibold text-teal">ClinicalRAG</p>
          <p className="mt-2 text-xs leading-5 text-slate-300">Grounded guideline console</p>
        </div>

        <nav className="space-y-1">
          {[
            ['query', 'Query'],
            ['audit', 'Audit'],
          ].map(([key, label]) => (
            <button
              className={`w-full rounded-md px-3 py-2 text-left text-sm font-semibold transition ${
                activeView === key ? 'bg-white text-navy' : 'text-slate-200 hover:bg-white/10'
              }`}
              key={key}
              type="button"
              onClick={() => setActiveView(key)}
            >
              {label}
            </button>
          ))}
          <button
            className={`w-full rounded-md px-3 py-2 text-left text-sm font-semibold transition ${
              ingestOpen ? 'bg-white text-navy' : 'text-slate-200 hover:bg-white/10'
            }`}
            type="button"
            onClick={() => {
              setActiveView('query')
              setIngestOpen(true)
              window.setTimeout(() => document.getElementById('ingest-title')?.focus(), 50)
            }}
          >
            Ingest
          </button>
        </nav>

        <div className="mt-7 rounded-lg border border-white/10 bg-white/5 p-3">
          <p className="text-xs font-semibold uppercase text-slate-400">Collections</p>
          <p className="mt-2 font-mono text-2xl text-white">{totalDocuments}</p>
          <p className="text-xs text-slate-300">indexed chunks</p>

          <div className="mt-4 space-y-2">
            {collections.map((collection) => (
              <div className="flex items-center justify-between gap-3 text-xs" key={collection.name}>
                <span className="truncate text-slate-300">{collection.name}</span>
                <span className="font-mono text-teal">{collection.document_count}</span>
              </div>
            ))}
          {!collections.length ? <p className="text-xs text-slate-400">No collections loaded</p> : null}
          </div>
        </div>

        <div className="mt-3 rounded-lg border border-white/10 bg-white/5 p-3">
          <p className="text-xs font-semibold uppercase text-slate-400">Provider</p>
          <p className="mt-2 text-sm font-semibold text-white">
            {health?.llm_configured
              ? health.llm_provider?.toUpperCase()
              : health
                ? 'ONNX + Chroma'
                : 'Unknown'}
          </p>
          <p className="mt-1 text-xs text-teal">
            {health
              ? health.llm_configured
                ? 'Generative mode'
                : 'Extractive mode'
              : 'Status unavailable'}
          </p>
        </div>

        <div className="mt-5">
          <DocumentIngester
            collection={selectedCollection}
            open={ingestOpen}
            onOpenChange={setIngestOpen}
            onIngested={() => setRefreshKey((value) => value + 1)}
          />
        </div>
      </aside>

      <main className="min-h-screen flex-1 lg:ml-[240px]">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-cream/95 px-5 py-4 backdrop-blur">
          <div className="mx-auto flex w-full max-w-5xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">
                {activeView === 'query' ? 'Guideline Query Console' : 'Operational Audit'}
              </p>
              <h1 className="mt-1 text-2xl font-semibold text-navy">
                {activeView === 'query' ? 'Clinical Decision Support' : 'Request Traceability'}
              </h1>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <select
                className="min-h-[38px] rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-teal focus:ring-2 focus:ring-teal/20"
                value={selectedCollection}
                onChange={(event) => setSelectedCollection(event.target.value)}
              >
                {collections.length ? (
                  collections.map((collection) => (
                    <option key={collection.name} value={collection.name}>
                      {collection.name}
                    </option>
                  ))
                ) : (
                  <option value="clinical_guidelines">clinical_guidelines</option>
                )}
              </select>
              <HealthDot ok={healthOk} llmConfigured={Boolean(health?.llm_configured)} />
            </div>
          </div>
        </header>

        <div className="px-5 py-6">
          {activeView === 'query' ? <QueryInterface collection={selectedCollection} /> : <AuditView />}
        </div>
      </main>
    </div>
  )
}
