<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { api } from './api'
import ImportDialog from './ImportDialog.vue'

const projects = ref([])
const summary = ref({ projectCount: 0, testDemandTotal: 0, estimatedDemandTotal: 0, pvtCount: 0 })
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
const emptyForm = () => ({ terminalCustomer: '', odmIntegrator: '', moduleFactory: '', projectName: '', application: '', stage: '', testDemandQuantity: '', estimatedTotalDemand: '', expectedMpDate: '', reportData: null })
const form = reactive(emptyForm())
const columns = [
  ['terminalCustomer', '终端客户'], ['odmIntegrator', 'ODM（原始设计制造商）集成商'], ['moduleFactory', '模组厂'], ['projectName', '项目名称'], ['application', '应用'], ['stage', '目前阶段'], ['testDemandQuantity', '测试阶段需求数量'], ['estimatedTotalDemand', '项目预计总需求量'], ['expectedMpDate', '预计 MP（量产）日期'],
]
const stageLabels = {
  EVT: 'EVT（工程验证测试）',
  DVT: 'DVT（设计验证测试）',
  PVT: 'PVT（生产验证测试）',
}
const visibleProjects = computed(() => projects.value)
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
let searchTimer
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
    const params = { search: search.value.trim(), stage: stageFilter.value }
    const [rows, stats] = await Promise.allSettled([api.projects(params), api.summary()])
    if (requestId !== refreshId) return
    const messages = []
    if (rows.status === 'fulfilled') {
      projects.value = rows.value
      const visibleIds = new Set(rows.value.map(project => project.id))
      selectedIds.value = selectedIds.value.filter(id => visibleIds.has(id))
    }
    else messages.push(`项目读取失败：${rows.reason.message}`)
    if (stats.status === 'fulfilled') summary.value = stats.value
    else { summary.value = null; messages.push(`统计暂不可用：${stats.reason.message}`) }
    error.value = messages.join('；')
  } catch (err) {
    error.value = `无法连接后端服务：${err.message}`
  } finally {
    if (requestId === refreshId) loading.value = false
  }
}

watch([search, stageFilter], () => {
  selectedIds.value = []
  clearTimeout(searchTimer)
  searchTimer = setTimeout(refresh, 250)
})

function openCreate() {
  formError.value = ''
  editingId.value = null
  Object.assign(form, emptyForm())
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
  if (deletingSelected.value) return
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
  if (deletingSelected.value || !selectedIds.value.length) return
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
onUnmounted(() => { clearTimeout(searchTimer); clearTimeout(toastTimer); refreshId++ })
</script>

<template>
  <div class="ocean-backdrop" aria-hidden="true"></div>
  <main class="page">
    <header class="topbar">
      <div class="brand"><div class="brandmark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><path d="M3 13c5-7 8 7 13 0s8 7 13 0M3 20c5-7 8 7 13 0s8 7 13 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div><div><h1>ODM 项目需求跟踪</h1><p>原始设计制造商 · 项目管理</p></div></div>
      <div class="actions">
        <button class="button" title="从 Excel（.xls / .xlsx）或 CSV（逗号分隔值）文件导入已填写的项目数据" @click="importOpen = true">导入项目数据</button>
        <a class="button" :href="api.exportUrl" title="导出全部项目及原始报告资料，格式为 CSV（逗号分隔值），可用 Excel 打开">导出项目数据</a>
        <a class="button" :href="api.exportReportUrl" title="仅导出含原开发报告资料的记录，格式为 CSV（逗号分隔值），可用 Excel 打开；备份全部项目请使用“导出项目数据”">导出开发报告</a>
        <button class="button primary" @click="openCreate">＋ 新建项目</button>
      </div>
    </header>

    <section class="workspace-intro" aria-labelledby="workspaceTitle">
      <div class="intro-copy"><p class="section-eyebrow"><span></span>项目管理 / 工作台</p><h2 id="workspaceTitle">项目需求，<em>一览清晰。</em></h2><p class="intro-description">从验证到量产，记录每一步项目进展。</p></div>
      <div class="workspace-note"><span class="status-dot"></span><span>本机数据工作空间</span><small>客户 · 项目 · 需求</small></div>
    </section>

    <section class="stats" aria-label="项目概览">
      <article class="stat"><span>项目总数</span><strong>{{ summary?.projectCount ?? '—' }}</strong></article>
      <article class="stat"><span>测试阶段需求总量</span><strong>{{ summary ? Number(summary.testDemandTotal).toLocaleString() : '—' }}<small>台</small></strong></article>
      <article class="stat"><span>项目预计总需求量</span><strong>{{ summary ? Number(summary.estimatedDemandTotal).toLocaleString() : '—' }}<small>台</small></strong></article>
      <article class="stat"><span>PVT（生产验证测试）阶段项目</span><strong>{{ summary?.pvtCount ?? '—' }}</strong></article>
    </section>

    <section class="panel">
      <div class="panel-heading"><div><span class="section-index">01 / 项目</span><h2>项目总览</h2></div><span class="panel-hint">集中查看与跟进项目需求</span></div>
      <div class="toolbar">
        <div class="filters"><input v-model="search" class="field search" type="search" placeholder="搜索客户、集成商、项目名称…" :disabled="deletingSelected"><select v-model="stageFilter" class="field stage-filter" :disabled="deletingSelected"><option value="">全部阶段</option><option value="EVT" title="工程验证测试阶段">EVT（工程验证）</option><option value="DVT" title="设计验证测试阶段">DVT（设计验证）</option><option value="PVT" title="生产验证测试阶段">PVT（生产验证）</option></select></div>
        <span class="count">{{ loading ? '加载中…' : `显示 ${visibleProjects.length} 个项目` }}</span>
      </div>
      <div v-if="selectedIds.length" class="selection-toolbar" role="status">
        <span>已选择 <strong>{{ selectedIds.length }}</strong> 个项目</span>
        <div><button class="button danger-outline" :disabled="deletingSelected" @click="removeSelectedProjects">{{ deletingSelected ? '正在删除…' : '删除已选项目' }}</button><button class="text-button" :disabled="deletingSelected" @click="clearSelection">取消选择</button></div>
      </div>
      <div v-if="error" class="error" role="alert">{{ error }}</div>
      <div class="table-wrap"><table><thead><tr><th class="selection-column"><input class="project-checkbox" type="checkbox" aria-label="全选当前显示项目" :checked="allVisibleSelected" :indeterminate="someVisibleSelected" :disabled="!visibleProjects.length || deletingSelected" @change="toggleVisibleSelection($event.target.checked)"></th><th v-for="[, label] in columns" :key="label">{{ label }}</th><th>操作</th></tr></thead>
        <tbody><tr v-for="p in visibleProjects" :key="p.id"><td class="selection-column"><input class="project-checkbox" type="checkbox" :aria-label="`选择项目 ${p.projectName}`" :checked="selectedIds.includes(p.id)" :disabled="deletingSelected" @change="toggleProjectSelection(p.id, $event.target.checked)"></td><td v-for="[key] in columns" :key="key">
          <span v-if="key === 'stage' && p[key]" class="stage" :class="p[key]">{{ stageLabels[p[key]] || p[key] }}</span>
          <template v-else-if="key === 'projectName'"><strong>{{ p[key] || '—' }}</strong><span v-if="p.reportData" class="source-badge">开发报告</span></template>
          <span v-else>{{ p[key] == null || p[key] === '' ? '—' : p[key] }}</span>
        </td><td class="row-actions"><button class="text-button" :disabled="deletingSelected" @click="openEdit(p)">编辑</button><button class="text-button danger" :disabled="deletingSelected" @click="removeProject(p)">删除</button></td></tr>
        <tr v-if="!visibleProjects.length"><td class="empty" :colspan="columns.length + 2"><div class="empty-orbit" aria-hidden="true">＋</div><strong>{{ loading ? '正在读取项目' : '还没有项目记录' }}</strong><span>新建项目，或点击“导入项目数据”选择已填写的数据文件。</span></td></tr></tbody>
      </table></div>
      <footer class="footer"><span>项目资料自动保存到本机。</span><span>“导出项目数据”可备份全部项目</span></footer>
    </section>

    <div v-if="modalOpen" class="overlay" @click.self="closeModal" @keydown.esc="closeModal">
      <section class="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle"><header class="modal-head"><h2 id="modalTitle">{{ editingId ? '编辑项目' : '新建项目' }}</h2><button class="close" aria-label="关闭" @click="closeModal">×</button></header>
        <form class="form-grid" @submit.prevent="saveProject">
          <div v-if="formError" class="error" role="alert" style="grid-column: 1 / -1">{{ formError }}</div>
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
    <ImportDialog v-if="importOpen" @close="importOpen = false" @imported="imported" />
    <div v-if="toast" class="toast" role="status">{{ toast }}</div>
  </main>
</template>
