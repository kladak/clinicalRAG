import { useState } from 'react'

import { api } from '../api/client.js'

const initialForm = {
  title: '',
  document_type: 'guideline',
  source_url: '',
  content: '',
}

export default function DocumentIngester({ collection, onIngested, open, onOpenChange }) {
  const [internalOpen, setInternalOpen] = useState(false)
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(null)
  const [error, setError] = useState('')
  const isOpen = open ?? internalOpen

  function toggleOpen() {
    const next = !isOpen
    if (onOpenChange) {
      onOpenChange(next)
    } else {
      setInternalOpen(next)
    }
  }

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setSuccess(null)

    try {
      const response = await api.ingest({
        ...form,
        collection,
      })
      setSuccess(response)
      setForm(initialForm)
      onIngested?.()
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to ingest document.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border-t border-white/10 pt-4">
      <button
        className="flex w-full items-center justify-between rounded-md px-2 py-2 text-left text-sm font-semibold text-white hover:bg-white/10"
        type="button"
        onClick={toggleOpen}
      >
        <span>Ingest Document</span>
        <span className="font-mono text-teal">{isOpen ? '-' : '+'}</span>
      </button>

      {isOpen ? (
        <form className="mt-3 space-y-3" onSubmit={handleSubmit}>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-300" htmlFor="ingest-title">
              Title
            </label>
            <input
              id="ingest-title"
              className="w-full rounded-md border border-white/10 bg-white/95 px-3 py-2 text-sm text-navy outline-none focus:border-teal focus:ring-2 focus:ring-teal/30"
              value={form.title}
              onChange={(event) => updateField('title', event.target.value)}
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-300" htmlFor="ingest-type">
              Document type
            </label>
            <select
              id="ingest-type"
              className="w-full rounded-md border border-white/10 bg-white/95 px-3 py-2 text-sm text-navy outline-none focus:border-teal focus:ring-2 focus:ring-teal/30"
              value={form.document_type}
              onChange={(event) => updateField('document_type', event.target.value)}
            >
              <option value="guideline">Guideline</option>
              <option value="protocol">Protocol</option>
              <option value="drug_label">Drug label</option>
              <option value="fhir">FHIR</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-300" htmlFor="ingest-url">
              Source URL
            </label>
            <input
              id="ingest-url"
              className="w-full rounded-md border border-white/10 bg-white/95 px-3 py-2 text-sm text-navy outline-none focus:border-teal focus:ring-2 focus:ring-teal/30"
              value={form.source_url}
              onChange={(event) => updateField('source_url', event.target.value)}
              placeholder="Optional"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-300" htmlFor="ingest-content">
              Content
            </label>
            <textarea
              id="ingest-content"
              className="min-h-[150px] w-full resize-y rounded-md border border-white/10 bg-white/95 px-3 py-2 text-sm leading-5 text-navy outline-none focus:border-teal focus:ring-2 focus:ring-teal/30"
              value={form.content}
              onChange={(event) => updateField('content', event.target.value)}
              required
            />
          </div>

          <button
            className="inline-flex min-h-[38px] w-full items-center justify-center gap-2 rounded-md bg-teal px-3 py-2 text-sm font-semibold text-white transition hover:bg-[#08998d] disabled:cursor-not-allowed disabled:bg-slate-500"
            type="submit"
            disabled={loading || !form.title.trim() || !form.content.trim()}
          >
            {loading ? <span className="spinner" aria-hidden="true" /> : null}
            {loading ? 'Ingesting' : 'Submit'}
          </button>

          {success ? (
            <div className="rounded-md border border-teal/40 bg-teal/10 px-3 py-2 text-xs text-white">
              Ingested - {success.chunks_created} chunks created
            </div>
          ) : null}

          {error ? (
            <div className="rounded-md border border-red-300/40 bg-red-500/10 px-3 py-2 text-xs text-red-100">
              {error}
            </div>
          ) : null}
        </form>
      ) : null}
    </div>
  )
}
