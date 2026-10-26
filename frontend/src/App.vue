<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { api } from './api'
import ImportDialog from './ImportDialog.vue'
import CustomerDialog from './CustomerDialog.vue'
import WeeklyUpdates from './WeeklyUpdates.vue'

const projects = ref([])
const customers = ref([])
const view = ref('customers')
const companyId = ref(null)
const companySearch = ref('')
const sidebarOpen = ref(false)
const customerOpen = ref(false)
const editingCustomer = ref(null)
const folderBusy = ref(false)
const assigning = ref(false)
const assignTarget = ref('__choose__')
const revision = ref(0)
const currentCompany = computed(() => customers.value.find(c => c.id === companyId.value) || null)
const filteredCustomers = computed(() => customers.value.filter(c => [c.fullName,c.shortName,c.contactName].some(v => v?.toLowerCase().includes(companySearch.value.trim().toLowerCase()))))
const bulkBusy = computed(() => deletingSelected.value || assigning.value)
const projectView = computed(() => ['projects','company','unassigned'].includes(view.value))
const viewTitle = computed(() => ({ customers:'客户公司',projects:'全部项目',weekly:'本周更新',unassigned:'未归属项目',company:currentCompany.value?.fullName || '客户公司' }[view.value]))
const search = ref('')
const stageFilter = ref('')
const modalOpen = ref(false)
const importOpen = ref(false)
const editingId = ref(null)
const loading = ref(false)
const deletingSelected = ref(false)
const selectedIds = ref([])
const saving = ref(false)
const formError = ref('')
const error = ref('')
const toast = ref('')
let toastTimer
const emptyForm = () => ({ customerId: null, terminalCustomer: '', odmIntegrator: '', moduleFactory: '', projectName: '', application: '', stage: '', testDemandQuantity: '', estimatedTotalDemand: '', expectedMpDate: '', reportData: null })
const form = reactive(emptyForm())
const columns = [
  ['customerName', '采购客户公司'],
  ['terminalCustomer', '终端客户'], ['odmIntegrator', 'ODM（原始设计制造商）集成商'], ['moduleFactory', '模组厂'], ['projectName', '项目名称'], ['application', '应用'], ['stage', '目前阶段'], ['testDemandQuantity', '测试阶段需求数量'], ['estimatedTotalDemand', '项目预计总需求量'], ['expectedMpDate', '预计 MP（量产）日期'],
]
const stageLabels = {
  EVT: 'EVT（工程验证测试）',
  DVT: 'DVT（设计验证测试）',
  PVT: 'PVT（生产验证测试）',
}
const visibleProjects = computed(() => projects.value.filter(p => {
  if (view.value === 'company' && p.customerId !== companyId.value) return false
  if (view.value === 'unassigned' && p.customerId != null) return false
  if (stageFilter.value && p.stage !== stageFilter.value) return false
  const query = search.value.trim().toLowerCase()
  return !query || [p.customerName,customerCandidate(p),p.terminalCustomer,p.odmIntegrator,p.moduleFactory,p.projectName,p.application].some(v => v?.toLowerCase().includes(query))
}))
function customerCandidate(project) {
  try {
    const raw = typeof project.reportData === 'string' ? JSON.parse(project.reportData) : project.reportData
    const value = Object.entries(raw?.fields || {}).find(([key]) => key.replace(/\s/g,'') === '客户')?.[1]
    return typeof value === 'string' && !['/','／'].includes(value.trim()) ? value.trim() : ''
  } catch { return '' }
}
const summary = computed(() => ({ projectCount: visibleProjects.value.length, testDemandTotal: visibleProjects.value.reduce((n,p) => n + Number(p.testDemandQuantity || 0),0), estimatedDemandTotal:visibleProjects.value.reduce((n,p) => n + Number(p.estimatedTotalDemand || 0),0), pvtCount:visibleProjects.value.filter(p => p.stage === 'PVT').length }))
const projectCount = id => projects.value.filter(p => p.customerId === id).length
const unassignedCount = computed(() => projects.value.filter(p => p.customerId == null).length)
const selectedVisibleCount = computed(() => visibleProjects.value.filter(project => selectedIds.value.includes(project.id)).length)
const allVisibleSelected = computed(() => visibleProjects.value.length > 0 && selectedVisibleCount.value === visibleProjects.value.length)
const someVisibleSelected = computed(() => selectedVisibleCount.value > 0 && !allVisibleSelected.value)
const formReport = computed(() => {
  if (!form.reportData) return null
  try {
    const report = typeof form.reportData === 'string' ? JSON.parse(form.reportData) : form.reportData
    return report && typeof report === 'object' && report.fields && typeof report.fields === 'object' && !Array.isArray(report.fields) ? report : null
  } catch { return null }
})
const formReportFields = computed(() => Object.entries(formReport.value?.fields || {}))
let refreshId = 0

function showToast(message) {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2400)
}

async function refresh() {
  const requestId = ++refreshId
  loading.value = true
  error.value = ''
  try {
    const [rows, companies] = await Promise.allSettled([api.projects(), api.customers()])
    if (requestId !== refreshId) return
    const messages = []
    if (rows.status === 'fulfilled') {
      projects.value = rows.value
      const visibleIds = new Set(rows.value.map(project => project.id))
      selectedIds.value = selectedIds.value.filter(id => visibleIds.has(id))
    }
    else { projects.value = []; selectedIds.value = []; messages.push(`项目读取失败：${rows.reason.message}`) }
    if (companies.status === 'fulfilled') customers.value = companies.value
    else { customers.value = []; selectedIds.value = []; messages.push(`客户读取失败：${companies.reason.message}`) }
    revision.value++
    error.value = messages.join('；')
  } catch (err) {
    error.value = `无法连接后端服务：${err.message}`
  } finally {
    if (requestId === refreshId) loading.value = false
  }
}

watch([search, stageFilter], () => {
  selectedIds.value = []
  assignTarget.value = '__choose__'
})

function navigate(next, id = null) {
  if (bulkBusy.value) return
  selectedIds.value = []; assignTarget.value = '__choose__'
  search.value = ''; stageFilter.value = ''; companyId.value = id; view.value = next
  sidebarOpen.value = false
}
function editCustomer(customer = null) { editingCustomer.value = customer; customerOpen.value = true }
async function savedCustomer(customer) {
  customerOpen.value = false
  await refresh()
  navigate('company', customer.id)
  showToast(customer.folderStatus === 'READY' ? '客户已保存' : '客户已保存，文件夹待创建，可在客户页面重试')
}
async function retryFolder() {
  if (folderBusy.value || !currentCompany.value) return
  const id = currentCompany.value.id
  folderBusy.value = true
  try { const result = await api.retryFolder(id); await refresh(); showToast(result.folderStatus === 'READY' ? '客户文件夹已创建' : '文件夹仍未创建，请检查桌面权限或同名目录') }
  catch (err) { error.value = err.message }
  finally { folderBusy.value = false }
}
function openProjectById(id) {
  const project = projects.value.find(p => p.id === id)
  if (!project) { showToast('该项目已不存在，请刷新'); return }
  navigate(project.customerId ? 'company' : 'unassigned', project.customerId || null)
  openEdit(project)
}
function openCustomerById(id) {
  const customer = customers.value.find(c => c.id === id)
  if (customer) navigate('company', id)
}
async function assignSelected() {
  if (bulkBusy.value || assignTarget.value === '__choose__') return
  const ids = visibleProjects.value.filter(p => selectedIds.value.includes(p.id)).map(p => p.id)
  if (!ids.length) return
  const target = assignTarget.value ? customers.value.find(c => c.id === Number(assignTarget.value)) : null
  if (assignTarget.value && !target) { error.value = '所选客户已不存在，请重新选择'; return }
  if (!window.confirm(`将已选 ${ids.length} 个项目归属到“${target?.fullName || '未归属项目'}”？`)) return
  assigning.value = true
  try { const result = await api.assign(ids, target?.id || null); selectedIds.value = []; assignTarget.value = '__choose__'; await refresh(); showToast(`已更新 ${result.updatedCount} 个项目的所属公司`) }
  catch (err) { error.value = err.message }
  finally { assigning.value = false }
}

function openCreate() {
  formError.value = ''
  editingId.value = null
  Object.assign(form, emptyForm())
  if (view.value === 'company') form.customerId = companyId.value
  modalOpen.value = true
}

function openEdit(project) {
  formError.value = ''
  editingId.value = project.id
  const initial = emptyForm()
  for (const key of Object.keys(initial)) form[key] = project[key] ?? initial[key]
  modalOpen.value = true
}

function closeModal() { if (!saving.value) modalOpen.value = false }

async function saveProject() {
  if (saving.value) return
  formError.value = ''
  if (!form.projectName.trim() || form.projectName.trim() === '/') { formError.value = '项目名称不能为空，也不能仅填写“/”'; return }
  const quantity = value => value === '' || value == null ? null : Number(value)
  const payload = {
    ...form,
    testDemandQuantity: quantity(form.testDemandQuantity),
    estimatedTotalDemand: quantity(form.estimatedTotalDemand),
    expectedMpDate: form.expectedMpDate || null,
  }
  if ([payload.testDemandQuantity, payload.estimatedTotalDemand].some(v => v != null && (!Number.isSafeInteger(v) || v < 0))) {
    formError.value = '需求数量必须为 0 到 9007199254740991 之间的整数'; return
  }
  saving.value = true
  try {
    if (editingId.value) await api.update(editingId.value, payload)
    else await api.create(payload)
    modalOpen.value = false
    showToast(editingId.value ? '项目已更新' : '项目已添加')
    await refresh()
  } catch (err) { formError.value = `保存失败：${err.message}` }
  finally { saving.value = false }
}

async function removeProject(project) {
  if (bulkBusy.value) return
  if (!window.confirm(`确认删除“${project.projectName}”吗？`)) return
  try { await api.remove(project.id); selectedIds.value = []; showToast('项目已删除'); await refresh() }
  catch (err) { error.value = `删除失败：${err.message}` }
}

function toggleProjectSelection(id, checked) {
  const selected = new Set(selectedIds.value)
  if (checked) selected.add(id)
  else selected.delete(id)
  selectedIds.value = [...selected]
}

function toggleVisibleSelection(checked) {
  const selected = new Set(selectedIds.value)
  for (const project of visibleProjects.value) {
    if (checked) selected.add(project.id)
    else selected.delete(project.id)
  }
  selectedIds.value = [...selected]
}

async function removeSelectedProjects() {
  if (bulkBusy.value || !selectedIds.value.length) return
  const selected = visibleProjects.value.filter(project => selectedIds.value.includes(project.id))
  if (!selected.length) { selectedIds.value = []; return }
  const names = selected.slice(0, 3).map(project => `· ${project.projectName}`).join('\n')
  const remaining = selected.length > 3 ? `\n· 以及其他 ${selected.length - 3} 个项目` : ''
  if (!window.confirm(`确认永久删除已选的 ${selected.length} 个项目吗？\n${names}${remaining}\n删除后无法恢复。`)) return

  deletingSelected.value = true
  const ids = selected.map(project => project.id)
  try {
    const result = await api.removeMany(ids)
    selectedIds.value = []
    showToast(`已删除 ${result.deletedCount ?? ids.length} 个项目`)
    await refresh()
  } catch (err) { error.value = `批量删除失败：${err.message}` }
  finally { deletingSelected.value = false }
}

function clearSelection() { selectedIds.value = [] }

async function imported(result) {
  importOpen.value = false
  showToast(`已新增 ${result.importedCount ?? 0} 条项目，完全重复跳过 ${result.skippedCount ?? 0} 条`)
  await refresh()
}

onMounted(refresh)
onUnmounted(() => { clearTimeout(toastTimer); refreshId++ })
</script>

<template>
  <div class="ocean-backdrop" aria-hidden="true"></div>
  <div class="workspace-shell">
    <button class="button mobile-nav-toggle" :aria-expanded="sidebarOpen" aria-controls="companySidebar" @click="sidebarOpen = !sidebarOpen">☰ 客户与本周更新</button>
    <aside id="companySidebar" class="company-sidebar" :class="{ 'is-open': sidebarOpen }" aria-label="业务导航">
      <div class="sidebar-brand">ODM <span>业务工作台</span></div>
      <nav class="primary-nav">
        <button :class="{ active: view === 'customers' }" :aria-current="view === 'customers' ? 'page' : undefined" :disabled="bulkBusy" @click="navigate('customers')">全部客户 <span>{{ customers.length }}</span></button>
        <button :class="{ active: view === 'projects' }" :disabled="bulkBusy" @click="navigate('projects')">全部项目 <span>{{ projects.length }}</span></button>
        <button :class="{ active: view === 'weekly' }" :aria-current="view === 'weekly' ? 'page' : undefined" :disabled="bulkBusy" @click="navigate('weekly')">◷ 本周更新</button>
        <button :class="{ active: view === 'unassigned' }" :disabled="bulkBusy" @click="navigate('unassigned')">未归属项目 <span>{{ unassignedCount }}</span></button>
      </nav>
      <div class="sidebar-divider"></div><label class="sidebar-label" for="companySearch">客户公司</label><input id="companySearch" v-model="companySearch" class="field sidebar-search" placeholder="搜索公司或联系人" :disabled="bulkBusy">
      <nav class="company-nav" aria-label="客户公司列表"><button v-for="c in filteredCustomers" :key="c.id" :class="{ active: view === 'company' && companyId === c.id }" :disabled="bulkBusy" @click="navigate('company', c.id)"><span>{{ c.shortName || c.fullName }}</span><small>{{ projectCount(c.id) }}</small></button></nav>
      <button class="button sidebar-create" :disabled="bulkBusy" @click="editCustomer()">＋ 新建客户公司</button><p class="sidebar-footnote">公司资料与项目保存在本机</p>
    </aside>
  <main class="page workspace-main">
    <header class="topbar">
      <div class="brand"><div class="brandmark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><path d="M3 13c5-7 8 7 13 0s8 7 13 0M3 20c5-7 8 7 13 0s8 7 13 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div><div><h1>ODM 项目需求跟踪</h1><p>原始设计制造商 · 项目管理</p></div></div>
      <div class="actions">
        <button class="button" @click="editCustomer()">＋ 新建客户</button>
        <button class="button" title="从 Excel（.xls / .xlsx）或 CSV（逗号分隔值）文件导入已填写的项目数据" @click="importOpen = true">导入项目数据</button>
        <a class="button" :href="api.exportUrl" title="导出全部项目及原始报告资料，格式为 CSV（逗号分隔值），可用 Excel 打开">导出项目数据</a>
        <a class="button" :href="api.exportReportUrl" title="仅导出含原开发报告资料的记录，格式为 CSV（逗号分隔值），可用 Excel 打开；备份全部项目请使用“导出项目数据”">导出开发报告</a>
        <button class="button primary" @click="openCreate">＋ 新建项目</button>
      </div>
    </header>

    <section class="workspace-intro" aria-labelledby="workspaceTitle">
      <div class="intro-copy"><p class="section-eyebrow"><span></span>客户业务 / 工作台</p><h2 id="workspaceTitle">{{ viewTitle }}</h2><p class="intro-description">{{ view === 'weekly' ? '本周新增和修改，在这里一起回看。' : '以公司集中查看项目，保留每一步业务变化。' }}</p></div>
      <div class="workspace-note"><span class="status-dot"></span><span>本机数据工作空间</span><small>客户 · 项目 · 需求</small></div>
    </section>

    <div v-if="error" class="error" role="alert">{{ error }}</div>
    <section v-if="view === 'customers'" class="panel">
      <div class="panel-heading"><div><span class="section-index">客户 / 公司</span><h2>客户公司</h2></div><span class="panel-hint">选择公司，集中查看所属项目和变化记录</span></div>
      <div class="company-grid"><button v-for="c in filteredCustomers" :key="c.id" class="company-card" @click="navigate('company', c.id)"><span class="company-monogram">{{ c.fullName.slice(0, 1) }}</span><h3>{{ c.fullName }}</h3><p>{{ c.contactName || '联系人待补充' }}<template v-if="c.shortName"> · {{ c.shortName }}</template></p><strong>{{ projectCount(c.id) }} 个项目 <span>查看公司业务 →</span></strong></button></div>
      <div v-if="!filteredCustomers.length" class="empty"><strong>{{ loading ? '正在读取客户' : '还没有匹配的客户公司' }}</strong><span>先建立实际采购公司的档案，再把项目归属到公司。</span><button class="button primary" @click="editCustomer()">＋ 新建客户公司</button></div>
    </section>
    <section v-if="view === 'company' && currentCompany" class="panel customer-profile">
      <div class="panel-heading"><div><span class="section-index">公司 / 客户资料</span><h2>{{ currentCompany.fullName }}</h2></div><button class="button" @click="editCustomer(currentCompany)">编辑客户资料</button></div>
      <dl class="customer-facts"><div><dt>简称</dt><dd>{{ currentCompany.shortName || '待补充' }}</dd></div><div><dt>联系人</dt><dd>{{ currentCompany.contactName || '待补充' }}</dd></div><div><dt>联系方式</dt><dd>{{ currentCompany.contactDetails || '待补充' }}</dd></div><div class="wide"><dt>备注</dt><dd>{{ currentCompany.notes || '暂无备注' }}</dd></div><div class="wide"><dt>桌面客户文件夹 · {{ currentCompany.folderStatus === 'READY' ? '已建立' : '待创建' }}</dt><dd class="folder-path">{{ currentCompany.archivePath || currentCompany.folderError || '保存客户后自动创建' }}</dd></div></dl>
      <p v-if="currentCompany.folderStatus === 'FAILED' && currentCompany.folderError" class="notice profile-actions">{{ currentCompany.folderError }}</p>
      <div class="profile-actions"><button class="button" :disabled="folderBusy" @click="retryFolder">{{ folderBusy ? '正在检查…' : currentCompany.folderStatus === 'READY' ? '检查客户文件夹' : '重试创建文件夹' }}</button><button class="button primary" @click="openCreate">＋ 新建该公司项目</button></div>
    </section>
    <WeeklyUpdates v-if="view === 'weekly'" :customers="customers" :existing-project-ids="projects.map(p => p.id)" :revision="revision" @open-project="openProjectById" @open-customer="openCustomerById" />
    <section v-if="projectView" class="stats" aria-label="当前项目列表概览">
      <article class="stat"><span>项目总数</span><strong>{{ summary?.projectCount ?? '—' }}</strong></article>
      <article class="stat"><span>测试阶段需求总量</span><strong>{{ summary ? Number(summary.testDemandTotal).toLocaleString() : '—' }}<small>台</small></strong></article>
      <article class="stat"><span>项目预计总需求量</span><strong>{{ summary ? Number(summary.estimatedDemandTotal).toLocaleString() : '—' }}<small>台</small></strong></article>
      <article class="stat"><span>PVT（生产验证测试）阶段项目</span><strong>{{ summary?.pvtCount ?? '—' }}</strong></article>
    </section>

    <section v-if="projectView" class="panel">
      <div class="panel-heading"><div><span class="section-index">01 / 项目</span><h2>{{ view === 'company' ? '该公司项目' : view === 'unassigned' ? '未归属项目' : '项目总览' }}</h2></div><span class="panel-hint">上方统计对应当前项目列表</span></div>
      <p v-if="view === 'unassigned'" class="unassigned-help">原表客户仅供核对。确认后先新建客户公司，再搜索原表客户、勾选对应项目并归属到公司。</p>
      <div class="toolbar">
        <div class="filters"><input v-model="search" class="field search" type="search" placeholder="搜索客户、集成商、项目名称…" :disabled="bulkBusy"><select v-model="stageFilter" class="field stage-filter" :disabled="bulkBusy"><option value="">全部阶段</option><option value="EVT" title="工程验证测试阶段">EVT（工程验证）</option><option value="DVT" title="设计验证测试阶段">DVT（设计验证）</option><option value="PVT" title="生产验证测试阶段">PVT（生产验证）</option></select></div>
        <span class="count">{{ loading ? '加载中…' : `显示 ${visibleProjects.length} 个项目` }}</span>
      </div>
      <div v-if="selectedIds.length" class="selection-toolbar" role="status">
        <span>已选择 <strong>{{ selectedIds.length }}</strong> 个项目</span>
        <div class="assignment-actions"><select v-model="assignTarget" class="field" :disabled="bulkBusy" aria-label="选择已勾选项目所属公司"><option value="__choose__" disabled>选择所属公司</option><option value="">暂不归属公司</option><option v-for="c in customers" :key="c.id" :value="String(c.id)">{{ c.fullName }}</option></select><button class="button" :disabled="bulkBusy || assignTarget === '__choose__'" @click="assignSelected">{{ assigning ? '正在归属…' : '归属到公司' }}</button><button class="button danger-outline" :disabled="bulkBusy" @click="removeSelectedProjects">{{ deletingSelected ? '正在删除…' : '删除已选项目' }}</button><button class="text-button" :disabled="bulkBusy" @click="clearSelection">取消选择</button></div>
      </div>
      <div class="table-wrap"><table><thead><tr><th class="selection-column"><input class="project-checkbox" type="checkbox" aria-label="全选当前显示项目" :checked="allVisibleSelected" :indeterminate="someVisibleSelected" :disabled="!visibleProjects.length || bulkBusy" @change="toggleVisibleSelection($event.target.checked)"></th><th v-for="[, label] in columns" :key="label">{{ label }}</th><th>操作</th></tr></thead>
        <tbody><tr v-for="p in visibleProjects" :key="p.id"><td class="selection-column"><input class="project-checkbox" type="checkbox" :aria-label="`选择项目 ${p.projectName}`" :checked="selectedIds.includes(p.id)" :disabled="bulkBusy" @change="toggleProjectSelection(p.id, $event.target.checked)"></td><td v-for="[key] in columns" :key="key">
          <span v-if="key === 'stage' && p[key]" class="stage" :class="p[key]">{{ stageLabels[p[key]] || p[key] }}</span>
          <template v-else-if="key === 'customerName' && !p.customerId"><span class="muted">未归属</span><small v-if="customerCandidate(p)" class="customer-candidate">原表：{{ customerCandidate(p) }}（待确认）</small></template>
          <template v-else-if="key === 'projectName'"><strong>{{ p[key] || '—' }}</strong><span v-if="p.reportData" class="source-badge">开发报告</span></template>
          <span v-else>{{ p[key] == null || p[key] === '' ? '—' : p[key] }}</span>
        </td><td class="row-actions"><button class="text-button" :disabled="bulkBusy" @click="openEdit(p)">编辑</button><button class="text-button danger" :disabled="bulkBusy" @click="removeProject(p)">删除</button></td></tr>
        <tr v-if="!visibleProjects.length"><td class="empty" :colspan="columns.length + 2"><div class="empty-orbit" aria-hidden="true">＋</div><strong>{{ loading ? '正在读取项目' : '还没有项目记录' }}</strong><span>新建项目，或点击“导入项目数据”选择已填写的数据文件。</span></td></tr></tbody>
      </table></div>
      <footer class="footer"><span>项目资料保存到本机。</span><span>“导出项目数据”导出全部项目，不包含客户完整档案和变更历史</span></footer>
    </section>
    <WeeklyUpdates v-if="view === 'company' && currentCompany" :key="companyId" :customer-id="companyId" scope="all" :customers="customers" :existing-project-ids="projects.map(p => p.id)" :revision="revision" @open-project="openProjectById" @open-customer="openCustomerById" />

    <div v-if="modalOpen" class="overlay" @click.self="closeModal" @keydown.esc="closeModal">
      <section class="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle"><header class="modal-head"><h2 id="modalTitle">{{ editingId ? '编辑项目' : '新建项目' }}</h2><button class="close" aria-label="关闭" @click="closeModal">×</button></header>
        <form class="form-grid" @submit.prevent="saveProject">
          <div v-if="formError" class="error" role="alert" style="grid-column: 1 / -1">{{ formError }}</div>
          <label class="wide">采购客户公司<select v-model="form.customerId"><option :value="null">暂不归属公司</option><option v-for="c in customers" :key="c.id" :value="c.id">{{ c.fullName }}</option></select></label>
          <label>终端客户<input v-model.trim="form.terminalCustomer"></label><label>ODM（原始设计制造商）集成商<input v-model.trim="form.odmIntegrator"></label>
          <label>模组厂<input v-model.trim="form.moduleFactory"></label><label>项目名称<input v-model.trim="form.projectName" required></label>
          <label>应用<input v-model.trim="form.application"></label><label>目前阶段<select v-model="form.stage"><option value="">请选择</option><option value="EVT">EVT（工程验证测试）</option><option value="DVT">DVT（设计验证测试）</option><option value="PVT">PVT（生产验证测试）</option></select></label>
          <label>测试阶段需求数量<input v-model="form.testDemandQuantity" type="number" min="0" step="1"></label><label>项目预计总需求量<input v-model="form.estimatedTotalDemand" type="number" min="0" step="1"></label>
          <label>预计 MP（量产）日期<input v-model="form.expectedMpDate" type="date"></label>
          <details v-if="form.reportData" class="report-details form-report-details"><summary>查看原开发报告（{{ formReportFields.length || '原始' }} 项）</summary><p v-if="formReport" class="report-origin">{{ formReport.file || '原报告' }} · {{ formReport.sheet || '工作表' }}<template v-if="formReport.row"> · 第 {{ formReport.row }} 行</template></p><dl v-if="formReportFields.length" class="report-fields"><template v-for="[label, value] in formReportFields" :key="label"><dt>{{ label }}</dt><dd>{{ value === '' || value == null ? '（空）' : value }}</dd></template></dl><p v-else class="muted">原报告内容已保留，但无法展开显示。</p></details>
          <div class="form-actions"><button type="button" class="button" :disabled="saving" @click="closeModal">取消</button><button type="submit" class="button primary" :disabled="saving">{{ saving ? '保存中…' : '保存项目' }}</button></div>
        </form>
      </section>
    </div>
    <CustomerDialog v-if="customerOpen" :customer="editingCustomer" :customers="customers" @close="customerOpen = false" @saved="savedCustomer" />
    <ImportDialog v-if="importOpen" :customers="customers" :default-customer-id="view === 'company' ? companyId : null" @close="importOpen = false" @imported="imported" />
    <div v-if="toast" class="toast" role="status">{{ toast }}</div>
  </main>
  </div>
</template>
