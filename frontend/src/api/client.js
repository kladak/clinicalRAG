import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = {
  query: (payload) => axios.post(`${BASE}/api/v1/query`, payload).then((r) => r.data),
  ingest: (payload) => axios.post(`${BASE}/api/v1/ingest`, payload).then((r) => r.data),
  health: () => axios.get(`${BASE}/api/v1/health`).then((r) => r.data),
  collections: () => axios.get(`${BASE}/api/v1/collections`).then((r) => r.data),
  audit: () => axios.get(`${BASE}/api/v1/audit`).then((r) => r.data),
}
