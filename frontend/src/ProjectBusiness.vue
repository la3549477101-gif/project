<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { api } from './api'
import ProjectDetailEditor from './ProjectDetailEditor.vue'
import FollowupComposer from './FollowupComposer.vue'
const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['close','changed'])
const details = ref([])
const stages = ref([])
const history = ref({ items: [], total: 0 })
const page = ref(0)
const tab = ref('details')
const showArchived = ref(false)
const editing = ref(false)
const editingDetail = ref(null)
const composing = ref(false)
const busy = ref(false)
const loading = ref(false)
const ready = ref(false)
const error = ref('')
let token = 0
const visibleDetails = computed(() => details.value.filter(d => showArchived.value || !d.archived))
const activeCount = computed(() => details.value.filter(d => !d.archived).length)
const stageSummary = computed(() => [...new Set(details.value.filter(d => !d.archived).map(d => d.businessStage || '待确认'))].join('、') || '尚无明细')
const decimalText = (value, empty = '待补') => value == null ? empty : String(value).replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '')
const testLabels = { EVT: 'EVT（工程验证测试）', DVT: 'DVT（设计验证测试）', PVT: 'PVT（生产验证测试）' }
const stamp = value => new Intl.DateTimeFormat('zh-CN', { timeZone:'Asia/Shanghai', dateStyle:'short', timeStyle:'short' }).format(new Date(value))
async function load() {
  const id = ++token
  loading.value = true; error.value = ''; ready.value = false
  try {
    const [rows, options, records] = await Promise.all([api.projectDetails(props.project.id), api.detailOptions(), api.followups(props.project.id, page.value)])
    if (id !== token) return
    details.value = rows; stages.value = options.businessStages; history.value = records; ready.value = true
  } catch (err) { if (id === token) error.value = `资料读取失败：${err.message}` }
  finally { if (id === token) loading.value = false }
}
load()
onUnmounted(() => { token++ })
function close() { if (!busy.value) emit('close') }
function edit(row = null) { error.value = ''; editingDetail.value = row; editing.value = true }
async function saveDetail(input) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { await api.saveDetail(props.project.id, editingDetail.value?.id, input); editing.value = false; emit('changed'); await load() }
  catch (err) { error.value = err.message }
  finally { busy.value = false }
}
async function saveFollowup(input) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { await api.appendFollowup(props.project.id, input); composing.value = false; page.value = 0; emit('changed'); await load() }
  catch (err) { error.value = err.message }
  finally { busy.value = false }
}
async function archive(row) {
  if (busy.value || !confirm(`${row.archived ? '恢复' : '归档'}“${row.materialModel || '型号待补'} / ${row.specification || '规格待补'}”？报价和跟进历史会保留。`)) return
  busy.value = true; error.value = ''
  try { await api.archiveDetail(props.project.id, row.id, !row.archived); emit('changed'); await load() }
  catch (err) { error.value = err.message }
  finally { busy.value = false }
}
async function turnPage(delta) { if (!loading.value && !busy.value) { page.value += delta; await load() } }
</script>
<template>
  <div class="overlay business-overlay" @click.self="close" @keydown.esc="close">
    <section class="modal business-modal" role="dialog" aria-modal="true" aria-labelledby="businessTitle">
      <header class="modal-head"><div><h2 id="businessTitle">{{ project.projectName }} · 项目业务</h2><p class="muted">{{ project.customerName || '暂未归属采购公司' }} · 测试阶段：{{ testLabels[project.stage] || '待补充' }}</p></div><button class="close" aria-label="关闭项目业务" :disabled="busy" @click="close">×</button></header>
      <div class="business-body">
        <div v-if="error" class="error" role="alert">{{ error }}<button v-if="!editing && !composing" class="text-button" :disabled="loading || busy" @click="load">重新读取</button></div>
        <div class="business-overview"><span><strong>{{ activeCount }}</strong> 个在跟进的型号规格</span><p>业务阶段：{{ stageSummary }}</p><small>各规格分别推进；项目数量和预测需求不会因新增明细而重复累计。</small></div>
        <nav class="business-tabs" aria-label="项目业务分组"><button class="button" :class="{ primary: tab === 'details' }" :disabled="busy || editing || composing" @click="tab = 'details'">型号规格与报价</button><button class="button" :class="{ primary: tab === 'history' }" :disabled="busy || editing || composing" @click="tab = 'history'">跟进与变更 · {{ history.total }}</button></nav>
        <ProjectDetailEditor v-if="editing" :key="editingDetail?.id || 'new'" :detail="editingDetail" :stages="stages" :saving="busy" @save="saveDetail" @cancel="editing = false" />
        <FollowupComposer v-else-if="composing" :details="details" :stages="stages" :saving="busy" @save="saveFollowup" @cancel="composing = false" />
        <template v-else-if="tab === 'details'">
          <div class="business-toolbar"><label class="import-check"><input v-model="showArchived" type="checkbox">包含已归档明细</label><button class="button primary" :disabled="busy || !ready || loading" @click="edit()">＋ 新增型号规格</button></div>
          <div class="business-detail-table"><table><thead><tr><th>材料型号 / 成品规格</th><th>业务交易阶段</th><th>当前报价与口径</th><th>预估需求与量产</th><th>操作</th></tr></thead><tbody>
            <tr v-for="row in visibleDetails" :key="row.id" :class="{ 'is-archived': row.archived }"><td><strong>{{ row.materialModel || '型号待补' }}</strong><span>{{ row.specification || '规格待补' }}</span><small>{{ row.productLine || '产品线待补' }} · {{ row.owner || '负责人待补' }}</small><small v-if="row.archived">已归档</small></td>
              <td><span class="business-stage">{{ row.businessStage || '待确认' }}</span><p>{{ row.statusNote || '暂无业务说明' }}</p></td>
              <td><strong>{{ decimalText(row.quotePrice, '待报价') }}</strong><span>{{ row.currency || '币种待补' }} / {{ row.quantityUnit || '单位待补' }}</span><small>{{ row.priceTerms || '计价与含税说明待补' }}</small><details v-if="row.competitor || row.competitorPrice != null || row.notes"><summary>其他资料</summary><p>竞争对手：{{ row.competitor || '待补' }}；单价：{{ decimalText(row.competitorPrice) }}</p><p>{{ row.notes }}</p></details></td>
              <td><span>年用量：{{ decimalText(row.estimatedAnnualQuantity) }} {{ row.quantityUnit }}</span><span>年营业额：{{ decimalText(row.estimatedAnnualRevenue) }} {{ row.currency }}</span><small>预估量产：{{ row.expectedMpText || '待补' }}</small></td>
              <td><div class="business-row-actions"><button v-if="!row.archived" class="text-button" :disabled="busy || loading" @click="edit(row)">编辑明细</button><button class="text-button" :disabled="busy || loading" @click="archive(row)">{{ row.archived ? '恢复明细' : '归档明细' }}</button></div></td></tr>
            <tr v-if="!visibleDetails.length"><td colspan="5" class="business-empty">{{ loading ? '正在读取型号规格…' : '暂无型号规格。请核对原项目资料后新增；旧报告不会自动拆分或合并。' }}</td></tr>
          </tbody></table></div>
        </template>
        <template v-else>
          <div class="business-toolbar"><p class="muted">业务跟进按发生日期、字段变更按保存日期倒序；录入时间另行保留</p><button class="button primary" :disabled="busy || loading || !ready" @click="composing = true; error = ''">＋ 新增业务跟进</button></div>
          <ol class="followup-list"><li v-for="row in history.items" :key="row.id"><div class="followup-heading"><time>{{ row.contactDate }}</time><span class="followup-kind">{{ row.kind === 'FIELD_CHANGE' ? '字段变更' : '业务跟进' }}</span><strong>{{ row.detailId ? `${row.materialModel || '型号待补'} / ${row.specification || '规格待补'}` : '项目整体' }}</strong></div><p class="followup-content">{{ row.content }}</p><p class="muted">资料来源：{{ row.source }}</p><p v-if="row.detailId" class="muted">保存时业务阶段：<template v-if="row.kind !== 'FIELD_CHANGE' && row.previousBusinessStage !== row.businessStage">{{ row.previousBusinessStage || '待确认' }} → </template>{{ row.businessStage || '待确认' }}</p><div v-if="row.nextAction || row.nextContactDate" class="followup-next"><span>下一步：{{ row.nextAction || '计划待补充' }}</span><small v-if="row.nextContactDate">下次跟进：{{ row.nextContactDate }}</small></div><small class="muted">记录 #{{ row.id }} · 录入于 {{ stamp(row.recordedAt) }}（北京时间）</small></li></ol>
          <p v-if="!history.items.length" class="business-empty">{{ loading ? '正在读取跟进…' : '还没有业务跟进记录。新增沟通、报价或验证进展后会保留在这里。' }}</p>
          <div class="business-history-pager"><button class="button" :disabled="busy || loading || page === 0" @click="turnPage(-1)">上一页</button><span>第 {{ page + 1 }} 页 · 共 {{ history.total }} 条</span><button class="button" :disabled="busy || loading || (page + 1) * 20 >= history.total" @click="turnPage(1)">下一页</button></div>
        </template>
      </div>
      <footer class="business-footer"><span>型号规格与跟进保存在项目内，订单模块后续接入；原表导出暂不包含这些新增资料。</span><button class="button" :disabled="busy" @click="close">关闭项目业务</button></footer>
    </section>
  </div>
</template>
