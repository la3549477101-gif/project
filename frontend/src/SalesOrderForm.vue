<script setup>
import { computed, nextTick, onUnmounted, reactive, ref } from 'vue'
import { api } from './api'
import SalesOrderSummary from './SalesOrderSummary.vue'
const props = defineProps({ customers:Array, projects:Array, defaultCustomerId:Number })
const emit = defineEmits(['close','saved'])
const form = reactive({ requestKey:crypto.randomUUID(), customerId:props.defaultCustomerId || null, customerOrderNo:'', orderDate:'', purpose:'', currency:'', source:'', notes:'' })
const projectId = ref(null)
const models = ref([])
const lines = ref([])
const error = ref('')
const busy = ref(false)
const modelsLoading = ref(false)
const preview = ref(null)
const pending = ref(null)
const bodyElement = ref(null)
let requestId = 0
let lineId = 0
const availableProjects = computed(() => props.projects.filter(p => p.customerId === form.customerId))
function resetCustomer() { projectId.value = null; models.value = []; lines.value = []; requestId++; modelsLoading.value = false; error.value = '' }
async function loadModels() {
  const token = ++requestId
  models.value = []; lines.value = []; error.value = ''
  if (!projectId.value) return
  modelsLoading.value = true
  try {
    const result = await api.projectDetails(projectId.value)
    if (token === requestId) { models.value = result.filter(d => !d.archived); addLine() }
  } catch (err) { if (token === requestId) error.value = err.message }
  finally { if (token === requestId) modelsLoading.value = false }
}
function addLine() { lines.value.push({ localId:++lineId, detailId:null, quantity:'', unit:'', unitPrice:'', expectedDeliveryDate:'', notes:'' }) }
function selectDetail(line) { line.unit = models.value.find(d => d.id === line.detailId)?.quantityUnit || ''; line.unitPrice = '' }
function quoteHint(line) { const d = models.value.find(d => d.id === line.detailId); return d?.quotePrice != null ? `项目参考报价：${d.quotePrice} ${d.currency || '币种待补'} / ${d.quantityUnit || '单位待补'}；请填写本次确认的成交价。` : '请根据本次订单依据填写成交价格，不推测价格。' }
function close() { if (!busy.value) emit('close') }
onUnmounted(() => { requestId++ })
async function review() {
  if (busy.value || modelsLoading.value) return
  error.value = ''; busy.value = true
  const input = { ...form, lines:lines.value.map(({localId,...line}) => ({...line, expectedDeliveryDate:line.expectedDeliveryDate || null})) }
  try { preview.value = await api.previewOrder(input); pending.value = input; await nextTick(); if (bodyElement.value) bodyElement.value.scrollTop = 0 }
  catch (err) { error.value = err.message }
  finally { busy.value = false }
}
async function editAgain() { preview.value = null; error.value = ''; await nextTick(); if (bodyElement.value) bodyElement.value.scrollTop = 0 }
async function save() {
  if (busy.value || !preview.value || !pending.value) return
  busy.value = true; error.value = ''
  try { emit('saved', await api.createOrder({...pending.value, reviewHash:preview.value.reviewHash})) }
  catch (err) { error.value = err.message }
  finally { busy.value = false }
}
</script>
<template>
  <div class="overlay business-overlay" @click.self="close" @keydown.esc="close">
    <section class="modal business-modal order-form-modal" role="dialog" aria-modal="true" aria-labelledby="orderFormTitle">
      <header class="modal-head"><div><h2 id="orderFormTitle">{{ preview ? '核对并确认订单' : '新建客户订单' }}</h2><p class="muted">样品单、量产单和后续采购分别保存；有明确采购依据才建立订单。</p></div><button class="close" :disabled="busy" aria-label="关闭新建订单" @click="close">×</button></header>
      <div v-if="error" class="error" role="alert">{{ error }}</div>
      <div ref="bodyElement" class="business-body">
        <SalesOrderSummary v-if="preview" :order="preview" />
        <form v-else id="salesOrderForm" class="form-grid business-editor" @submit.prevent="review">
          <label>采购客户<select v-model="form.customerId" required :disabled="busy" @change="resetCustomer"><option :value="null">请选择</option><option v-for="c in customers" :key="c.id" :value="c.id">{{ c.fullName }}</option></select></label>
          <label>所属项目<select v-model="projectId" required :disabled="busy || !form.customerId" @change="loadModels"><option :value="null">请选择</option><option v-for="p in availableProjects" :key="p.id" :value="p.id">{{ p.projectName }}</option></select></label>
          <p v-if="form.customerId && !availableProjects.length" class="notice wide">该客户尚无已归属项目。请先新建项目，并在“规格与跟进”中添加型号规格。</p>
          <label>订单用途<select v-model="form.purpose" required :disabled="busy"><option value="">请选择</option><option value="SAMPLE">样品单</option><option value="MASS_PRODUCTION">量产单</option></select></label>
          <label>下单日期<input v-model="form.orderDate" type="date" required :disabled="busy"></label>
          <label>客户订单号（可留空）<input v-model.trim="form.customerOrderNo" maxlength="100" :disabled="busy"></label>
          <label>本单币种<input v-model.trim="form.currency" aria-label="本单币种" list="orderCurrencyOptions" placeholder="CNY：人民币；USD：美元" maxlength="3" required :disabled="busy"><datalist id="orderCurrencyOptions"><option value="CNY">人民币</option><option value="USD">美元</option><option value="EUR">欧元</option><option value="HKD">港币</option><option value="JPY">日元</option><option value="GBP">英镑</option></datalist></label>
          <div class="wide order-lines-editor"><div class="order-line-title"><h3>订单明细</h3><button type="button" class="button" :disabled="busy || !models.length || lines.length >= 200" @click="addLine">＋ 添加明细</button></div>
            <p v-if="modelsLoading" class="muted">正在读取型号规格…</p><p v-else-if="projectId && !models.length" class="notice">没有可用型号规格，请先在项目中新增或恢复明细。</p>
            <fieldset v-for="(line,index) in lines" :key="line.localId" class="order-line-form" :disabled="busy"><legend>第 {{ index + 1 }} 项</legend><div class="form-grid">
              <label class="wide">型号规格<select v-model="line.detailId" required @change="selectDetail(line)"><option :value="null">请选择</option><option v-for="d in models" :key="d.id" :value="d.id" :disabled="lines.some(other => other !== line && other.detailId === d.id)">{{ d.materialModel || '型号待补' }} / {{ d.specification || '规格待补' }}</option></select></label>
              <label>本次数量<input v-model.trim="line.quantity" inputmode="decimal" maxlength="30" required></label><label>数量及计价单位<input v-model.trim="line.unit" maxlength="30" required placeholder="件、千克、米等实际单位"></label>
              <label>本次含税成交单价<input v-model.trim="line.unitPrice" inputmode="decimal" maxlength="30" required></label><label>约定交期（可留空）<input v-model="line.expectedDeliveryDate" type="date"></label>
              <p class="field-hint wide">{{ quoteHint(line) }}</p><label class="wide">明细备注<input v-model.trim="line.notes" maxlength="1000"></label>
              <div class="wide"><button type="button" class="text-button danger" @click="lines.splice(index,1)">移除本行</button></div>
            </div></fieldset>
          </div>
          <label class="wide">已确认采购的订单依据<textarea v-model.trim="form.source" maxlength="1000" rows="2" required :disabled="busy" placeholder="例如：客户采购订单、确认下单的邮件或聊天记录及日期"></textarea></label>
          <label class="wide">订单备注<textarea v-model.trim="form.notes" maxlength="2000" rows="2" :disabled="busy"></textarea></label>
          <p class="muted wide">数量和单价最多13位整数、6位小数；下一步由系统计算每行含税金额及总额，并展示客户条件供你核对。当前一张订单只包含同一项目的型号规格。</p>
        </form>
      </div>
      <footer class="business-footer"><span>{{ preview ? '确认前请检查客户、型号、数量、单位及金额。已保存订单本期不提供覆盖编辑或删除。' : '这一步只生成预览，不会写入正式订单。' }}</span><div class="order-footer-actions"><button v-if="preview" class="button" :disabled="busy" @click="editAgain">返回修改</button><button v-else class="button" :disabled="busy" @click="close">取消</button><button v-if="preview" type="button" class="button primary" :disabled="busy" @click="save">{{ busy ? '保存中…' : preview.id ? '查看已保存订单' : '确认保存订单' }}</button><button v-else class="button primary" form="salesOrderForm" :disabled="busy || modelsLoading || !lines.length">{{ busy ? '生成预览…' : '预览并核对订单' }}</button></div></footer>
    </section>
  </div>
</template>
