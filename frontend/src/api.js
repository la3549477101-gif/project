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
  reportDefaults: () => request(`${SPRING}/report/defaults`),
  saveReportDefaults: body => request(`${SPRING}/report/defaults`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),
  reportRows: () => request(`${SPRING}/report/rows`),
  saveReportRow: (id,body) => request(`${SPRING}/report/rows${id?'/'+id:''}`,{method:id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),
  reportWorkbookUrl: `${FLASK}/export/report.xlsx`,
  orders: (filters = {}) => request(`${SPRING}/orders?${new URLSearchParams(Object.entries(filters).filter(([,v]) => v != null && v !== ''))}`),
  order: id => request(`${SPRING}/orders/${id}`),
  previewOrder: body => request(`${SPRING}/orders/preview`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) }),
  createOrder: body => request(`${SPRING}/orders`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) }),
  orderExportUrl: customerId => `${SPRING}/orders/export${customerId ? '?customerId=' + customerId : ''}`,
  customers: () => request(`${SPRING}/customers`),
  customerProfileSchema: () => request(`${SPRING}/customers/profile-schema`),
  detailOptions: () => request(`${SPRING}/projects/detail-options`),
  setPriority: (id, important) => request(`${SPRING}/projects/${id}/priority`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ important }) }),
  projectDetails: (id) => request(`${SPRING}/projects/${id}/details`),
  saveDetail: (projectId, id, detail) => request(`${SPRING}/projects/${projectId}/details${id ? '/' + id : ''}`, { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(detail) }),
  archiveDetail: (projectId, id, archived) => request(`${SPRING}/projects/${projectId}/details/${id}/archive`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ archived }) }),
  followups: (id, page = 0) => request(`${SPRING}/projects/${id}/followups?page=${page}&size=20`),
  appendFollowup: (id, followup) => request(`${SPRING}/projects/${id}/followups`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(followup) }),
  createCustomer: (customer) => request(`${SPRING}/customers`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(customer) }),
  updateCustomer: (id, customer) => request(`${SPRING}/customers/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(customer) }),
  retryFolder: (id) => request(`${SPRING}/customers/${id}/folder/retry`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }),
  assign: (ids, customerId) => request(`${SPRING}/projects/assign`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids, customerId }) }),
  activities: (filters) => request(`${SPRING}/activities?${new URLSearchParams(Object.entries(filters).filter(([, value]) => value != null && value !== ''))}`),
  projects: (filters = {}) => {
    const query = new URLSearchParams()
    if (filters.search) query.set('search', filters.search)
    if (filters.stage) query.set('stage', filters.stage)
    if (filters.customerId) query.set('customerId', filters.customerId)
    if (filters.unassigned) query.set('unassigned', 'true')
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
