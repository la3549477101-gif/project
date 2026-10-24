<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { api } from './api'

const emit = defineEmits(['close', 'imported'])
const dialog = ref(null)
const fileInput = ref(null)
const fileName = ref('')
const sheets = ref([])
const fileWarnings = ref([])
const sheetIndex = ref(0)
const previewing = ref(false)
const importing = ref(false)
const error = ref('')
const onlyPending = ref(false)
const page = ref(1)
const pageSize = 25
let previewId = 0

const sheet = computed(() => sheets.value[sheetIndex.value] || null)
const rows = computed(() => sheet.value?.rows || [])
const formatLabel = format => ({ basic: '项目清单', report: '开发报告', unsupported: '未识别格式' }[format] || '未识别格式')
const messages = value => Array.isArray(value) ? value.map(String) : []

function nameError(value) {
  if (value != null && typeof value !== 'string') return '项目名称必须为文本。'
  const name = (value || '').trim()
  if (!name || name === '/' || name === '／') return '项目名称不能为空，也不能仅填写“/”或“／”。'
  if (name.length > 255) return '项目名称不能超过 255 字，请缩短后导入。'
  return ''
}

function dateError(value) {
  if (!value) return ''
  const text = String(value)
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text)
  if (!match) return '预计 MP（量产）日期请填写有效的年、月、日，也可留空。'
  const [, year, month, day] = match.map(Number)
  const date = new Date(0)
  date.setUTCFullYear(year, month - 1, day)
  date.setUTCHours(0, 0, 0, 0)
  return year < 1 || date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day
    ? '预计 MP（量产）日期无效，请更正或留空。' : ''
}

function isNameMessage(message) { return /^项目名称/.test(message) }
function isDateMessage(message) { return /^预计\s*(?:MP|ＭＰ|量产|MP（量产）|MP\(量产\))?\s*(?:日期|时间)/i.test(message) }

function rowDateError(row) {
  const invalid = dateError(row.project.expectedMpDate)
  if (invalid) return invalid
  return !row.dateReviewed && row.errors.some(isDateMessage) ? '原表量产日期未通过校验，请选择精确日期，或点击“留空”确认。' : ''
}

function rowErrors(row) {
  const current = []
  const name = nameError(row.project.projectName)
  const date = rowDateError(row)
  if (name) current.push(name)
  if (date) current.push(date)
  for (const message of row.errors) {
    if (isNameMessage(message) || isDateMessage(message)) continue
    current.push(message)
  }
  return [...new Set(current)]
}

function originalErrorResolved(row, message) {
  if (isNameMessage(message)) return !nameError(row.project.projectName)
  if (isDateMessage(message)) return !rowDateError(row)
  return false
}

const pendingRows = computed(() => rows.value.filter(row => rowErrors(row).length || (row.needsReview && !row.selected)))
const pendingCount = computed(() => pendingRows.value.length)
const readyRows = computed(() => rows.value.filter(row => !rowErrors(row).length))
const selectedRows = computed(() => rows.value.filter(row => row.selected && !rowErrors(row).length))
const filteredRows = computed(() => onlyPending.value ? pendingRows.value : rows.value)
const pageCount = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / pageSize)))
const visibleRows = computed(() => filteredRows.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const allReadySelected = computed(() => readyRows.value.length > 0 && readyRows.value.every(row => row.selected))

watch([sheetIndex, onlyPending], () => { page.value = 1 })
watch(pageCount, count => { if (page.value > count) page.value = count })

function editRow(row, field) {
  if (field === 'date') row.dateReviewed = true
  if (rowErrors(row).length) { row.selected = false; row.needsReview = true }
}

function clearDate(row) {
  row.project.expectedMpDate = ''
  editRow(row, 'date')
}

function toggleAll(event) {
  for (const row of rows.value) row.selected = event.target.checked && !rowErrors(row).length
}

function reportMetadata(value) {
  if (!value) return null
  try {
    const data = typeof value === 'string' ? JSON.parse(value) : value
    return data && typeof data === 'object' && data.fields && typeof data.fields === 'object' && !Array.isArray(data.fields) ? data : null
  } catch { return null }
}

function reportFields(row) { return Object.entries(reportMetadata(row.project.reportData)?.fields || {}) }

async function chooseFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || importing.value) return
  const requestId = ++previewId
  fileName.value = file.name
  error.value = ''
  sheets.value = []
  fileWarnings.value = []
  sheetIndex.value = 0
  onlyPending.value = false
  page.value = 1
  if (!/\.(csv|xls|xlsx)$/i.test(file.name)) {
    error.value = '请选择 CSV（逗号分隔值）、Excel .xls 或 .xlsx 表格。Word、PDF 和截图暂不支持。文件夹请打开后，选择里面的表格文件。'
    return
  }
  previewing.value = true
  try {
    const result = await api.previewImport(file)
    if (requestId !== previewId) return
    fileName.value = result.fileName || file.name
    fileWarnings.value = messages(result.warnings)
    sheets.value = (Array.isArray(result.sheets) ? result.sheets : []).map((item, index) => ({
      ...item,
      name: item.name || `工作表 ${index + 1}`,
      headers: Array.isArray(item.headers) ? item.headers : [],
      warnings: messages(item.warnings),
      rows: (Array.isArray(item.rows) ? item.rows : []).map((row, rowIndex) => {
        const project = { ...(row.project || {}) }
        project.projectName = String(project.projectName || '')
        project.expectedMpDate = project.expectedMpDate || ''
        const prepared = { ...row, key: `${index}-${rowIndex}`, project, errors: messages(row.errors), warnings: messages(row.warnings), selected: false, needsReview: false, dateReviewed: false }
        prepared.selected = !prepared.errors.length && !rowErrors(prepared).length
        prepared.needsReview = !prepared.selected
        return prepared
      }),
    }))
    const firstSupported = sheets.value.findIndex(item => item.format !== 'unsupported' && item.rows.length > 0)
    sheetIndex.value = firstSupported >= 0 ? firstSupported : 0
    if (!sheets.value.length) error.value = '文件中没有可预览的工作表，请检查文件是否包含表头和数据。'
  } catch (err) {
    if (requestId === previewId) error.value = `预览失败：${err.message}`
  } finally {
    if (requestId === previewId) previewing.value = false
  }
}

function close() {
  if (importing.value) return
  previewId++
  emit('close')
}

async function confirm() {
  if (importing.value || previewing.value || !sheet.value || sheet.value.format === 'unsupported') return
  error.value = ''
  const invalidSelected = rows.value.some(row => row.selected && rowErrors(row).length)
  if (invalidSelected) {
    error.value = '已选记录中仍有待更正内容，请补全或取消选择后再导入。'
    return
  }
  if (!selectedRows.value.length) { error.value = '请先选择至少一条校验通过的记录。'; return }
  const projects = selectedRows.value.map(row => ({
    ...row.project,
    projectName: String(row.project.projectName).trim(),
    expectedMpDate: row.project.expectedMpDate || null,
  }))
  importing.value = true
  try {
    const result = await api.confirmImport(projects)
    emit('imported', result)
  } catch (err) { error.value = `导入失败：${err.message}` }
  finally { importing.value = false }
}

onMounted(async () => { await nextTick(); dialog.value?.focus() })
</script>

<template>
  <div ref="dialog" class="overlay import-overlay" tabindex="-1" @click.self="close" @keydown.esc="close">
    <section class="modal import-modal" role="dialog" aria-modal="true" aria-labelledby="importTitle" :aria-busy="previewing || importing">
      <header class="modal-head"><div><h2 id="importTitle">导入项目数据</h2><p class="import-subtitle">先预览和补全，确认后才会保存项目。</p></div><button class="close" :disabled="importing" aria-label="关闭导入" @click="close">×</button></header>
      <div class="import-body">
        <div class="import-file-picker">
          <div><strong>{{ fileName || '选择已填写的项目数据文件' }}</strong><p>支持 CSV（逗号分隔值）、Excel .xls 和 .xlsx；文件夹请打开后选择里面的表格。Word、PDF 和截图暂不支持。</p></div>
          <button class="button" :disabled="previewing || importing" @click="fileInput.click()">{{ fileName ? '重新选择数据文件' : '选择数据文件' }}</button>
          <input ref="fileInput" class="hidden" type="file" accept=".csv,.xls,.xlsx,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" aria-label="选择项目数据文件" :disabled="previewing || importing" @change="chooseFile">
        </div>
        <p class="import-notice">完全相同的记录会跳过；修改过内容的记录会新增。本次导入不会自动覆盖已有记录，同名项目也会保留各自的型号、规格等报告内容。</p>
        <div v-if="error" class="error import-error" role="alert">{{ error }}</div>
        <ul v-if="fileWarnings.length" class="import-warning-list"><li v-for="(warning, index) in fileWarnings" :key="index">{{ warning }}</li></ul>
        <div v-if="previewing" class="import-state" role="status"><strong>正在解析表格…</strong><span>解析完成后，可选择工作表并检查每条记录。</span></div>
        <template v-else-if="sheets.length">
          <div class="import-sheet-toolbar">
            <label class="import-sheet-label">工作表<select v-model.number="sheetIndex" class="field" :disabled="importing"><option v-for="(item, index) in sheets" :key="index" :value="index">{{ item.name }} · {{ formatLabel(item.format) }} · {{ item.rows.length }} 条</option></select></label>
            <span class="muted">本次只导入当前工作表，其他工作表可再次选择文件导入。</span>
          </div>
          <ul v-if="sheet.warnings.length" class="import-warning-list"><li v-for="(warning, index) in sheet.warnings" :key="index">{{ warning }}</li></ul>
          <div v-if="sheet.format === 'unsupported'" class="import-state"><strong>这个工作表暂不支持导入</strong><span>未识别为项目清单或开发报告。请切换工作表，或在原表中核对表头后重新选择文件。</span><details v-if="sheet.headers.length"><summary>查看读取到的表头</summary><p>{{ sheet.headers.join('、') }}</p></details></div>
          <div v-else-if="!rows.length" class="import-state"><strong>已识别{{ formatLabel(sheet.format) }}，没有项目记录</strong><span>如果这是空模板，请先填写项目数据，保存后重新选择文件。</span></div>
          <template v-else>
            <div class="import-selection-toolbar">
              <label class="import-check"><input type="checkbox" :checked="allReadySelected" :disabled="!readyRows.length || importing" @change="toggleAll">选择全部可导入记录（{{ readyRows.length }}）</label>
              <label class="import-check"><input v-model="onlyPending" type="checkbox" :disabled="importing">仅显示待处理记录（{{ pendingCount }}）</label>
              <span class="count">解析 {{ rows.length }} 条 · 已选 {{ selectedRows.length }} 条</span>
            </div>
            <p class="import-help">项目名称必填，“/”或“／”视为空，名称过长时请缩短。量产日期可留空；填写时请选择精确日期。补全后请勾选该行。仍有校验错误时，请回原表更正后重新选择文件。</p>
            <div class="import-table-wrap">
              <table class="import-table">
                <thead><tr><th>选择</th><th>原表行号</th><th>项目名称（可补填）</th><th>终端客户</th><th>ODM（原始设计制造商）集成商</th><th>模组厂</th><th>应用</th><th>目前阶段</th><th>测试需求数量</th><th>预计总需求量</th><th>预计 MP（量产）日期（可补填）</th></tr></thead>
                <tbody>
                  <template v-for="row in visibleRows" :key="row.key">
                    <tr :class="{ 'import-row-invalid': rowErrors(row).length }">
                      <td><input v-model="row.selected" type="checkbox" :disabled="!!rowErrors(row).length || importing" :aria-label="`选择原表第 ${row.rowNumber} 行`"></td>
                      <td>{{ row.rowNumber }}</td>
                      <td><input v-model="row.project.projectName" class="import-edit-name" :disabled="importing" :aria-label="`原表第 ${row.rowNumber} 行项目名称`" :aria-invalid="!!nameError(row.project.projectName)" @input="editRow(row)"></td>
                      <td>{{ row.project.terminalCustomer || '—' }}</td><td>{{ row.project.odmIntegrator || '—' }}</td><td>{{ row.project.moduleFactory || '—' }}</td><td>{{ row.project.application || '—' }}</td><td>{{ row.project.stage || '—' }}</td><td>{{ row.project.testDemandQuantity ?? '—' }}</td><td>{{ row.project.estimatedTotalDemand ?? '—' }}</td>
                      <td><div class="import-date-editor"><input v-model="row.project.expectedMpDate" type="date" :disabled="importing" :aria-label="`原表第 ${row.rowNumber} 行预计量产日期`" :aria-invalid="!!rowDateError(row)" @input="editRow(row, 'date')"><button class="text-button" :disabled="importing" :aria-label="`将原表第 ${row.rowNumber} 行预计量产日期留空`" @click="clearDate(row)">留空</button></div></td>
                    </tr>
                    <tr class="import-row-notes"><td colspan="11">
                      <div class="import-row-status" :class="rowErrors(row).length ? 'is-pending' : 'is-ready'">{{ rowErrors(row).length ? '待更正：' + rowErrors(row).join('；') : '校验通过，可选择导入' }}</div>
                      <ul v-if="row.errors.length" class="import-original-errors"><li v-for="(message, index) in row.errors" :key="index" :class="{ resolved: originalErrorResolved(row, message) }">{{ originalErrorResolved(row, message) ? '已修正 · ' : '原表校验 · ' }}{{ message }}</li></ul>
                      <ul v-if="row.warnings.length" class="import-row-warnings"><li v-for="(warning, index) in row.warnings" :key="index">提示 · {{ warning }}</li></ul>
                      <details v-if="row.project.reportData" class="report-details"><summary>查看本行原开发报告（{{ reportFields(row).length || '原始' }} 项）</summary><dl v-if="reportFields(row).length" class="report-fields"><template v-for="[label, value] in reportFields(row)" :key="label"><dt>{{ label }}</dt><dd>{{ value === '' || value == null ? '（空）' : value }}</dd></template></dl><p v-else class="muted">原报告内容已保留，但无法展开显示。</p></details>
                    </td></tr>
                  </template>
                  <tr v-if="!visibleRows.length"><td colspan="11" class="import-no-rows">当前没有待补全或待更正的记录，可取消筛选查看全部项目。</td></tr>
                </tbody>
              </table>
            </div>
            <div class="import-pagination"><span>共 {{ filteredRows.length }} 条，每页 {{ pageSize }} 条</span><div><button class="button" :disabled="page <= 1 || importing" @click="page--">上一页</button><span>第 {{ page }} / {{ pageCount }} 页</span><button class="button" :disabled="page >= pageCount || importing" @click="page++">下一页</button></div></div>
          </template>
        </template>
        <div v-else-if="!error" class="import-state"><strong>先选择数据文件，查看导入预览</strong><span>支持九字段项目清单与开发报告。开发报告的原始字段会随项目一并保留。</span></div>
      </div>
      <footer class="import-footer"><span>{{ sheet && sheet.format !== 'unsupported' ? `当前工作表：${sheet.name}` : '取消后不会保存任何项目' }}</span><div><button class="button" :disabled="importing" @click="close">取消</button><button class="button primary" :disabled="previewing || importing || !selectedRows.length || sheet?.format === 'unsupported'" @click="confirm">{{ importing ? '正在导入…' : `确认导入 ${selectedRows.length} 条` }}</button></div></footer>
    </section>
  </div>
</template>
