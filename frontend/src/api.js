const SPRING = import.meta.env.VITE_SPRING_API || 'http://localhost:8080/api'
const FLASK = import.meta.env.VITE_FLASK_API || 'http://localhost:5000/api'

async function request(url, options = {}) {
  const response = await fetch(url, options)
  if (!response.ok) {
    const text = await response.text()
    let detail
    try { const body = JSON.parse(text); detail = body.message || body.detail || body.error }
    catch { detail = text.length < 300 && !text.includes('<') ? text : null }
    throw new Error(detail || `请求失败 (${response.status})`)
  }
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  projects: (filters = {}) => {
    const query = new URLSearchParams()
    if (filters.search) query.set('search', filters.search)
    if (filters.stage) query.set('stage', filters.stage)
    return request(`${SPRING}/projects?${query}`)
  },
  create: (project) => request(`${SPRING}/projects`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(project),
  }),
  update: (id, project) => request(`${SPRING}/projects/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(project),
  }),
  remove: (id) => request(`${SPRING}/projects/${id}`, { method: 'DELETE' }),
  removeMany: (ids) => request(`${SPRING}/projects/bulk-delete`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(ids),
  }),
  summary: () => request(`${FLASK}/summary`),
  exportUrl: `${FLASK}/export/csv`,
  exportReportUrl: `${FLASK}/export/report`,
  previewImport: (file) => {
    const body = new FormData()
    body.append('file', file)
    return request(`${FLASK}/import/preview`, { method: 'POST', body })
  },
  confirmImport: (projects) => request(`${FLASK}/import/confirm`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ projects }),
  }),
  importCsv: (file) => {
    const body = new FormData()
    body.append('file', file)
    return request(`${FLASK}/import/csv`, { method: 'POST', body })
  },
}
