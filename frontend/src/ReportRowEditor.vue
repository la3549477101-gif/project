<script setup>
import { reactive, ref, watch } from 'vue'
import { api } from './api'
import { reportFields } from './report-fields'
import { initialReportForm } from './report-preferences'
const props=defineProps({row:Object,customers:Array,defaultCustomerId:Number,initialDefaults:Object})
const emit=defineEmits(['close','saved'])
const form=reactive(initialReportForm(props.row,props.initialDefaults,props.defaultCustomerId))
const saving=ref(false),error=ref(''),stages=ref([])
watch(()=>form.customerId,id=>{if(id){const c=props.customers.find(c=>c.id===id);if(c)form.fields.customerName=c.fullName}},{immediate:true})
api.detailOptions().then(r=>stages.value=r.businessStages).catch(()=>{})
async function save() {
  if(saving.value)return
  saving.value=true;error.value=''
  try { const saved=await api.saveReportRow(props.row?.projectId,{...form,customerId:form.customerId||null});emit('saved',saved) }
  catch(e){error.value=e.message}
  finally{saving.value=false}
}
function close(){if(!saving.value)emit('close')}
</script>
<template>
  <div class="overlay business-overlay" @click.self="close" @keydown.esc="close"><section class="modal business-modal report-editor" role="dialog" aria-modal="true" aria-labelledby="reportEditorTitle">
    <header class="modal-head"><div><h2 id="reportEditorTitle">{{row?'编辑项目报告行':'新建项目报告行'}}</h2><p class="muted">按项目开发表集中填写，核对后一次保存；取消不写入。</p></div><button class="close" aria-label="关闭报告行编辑" :disabled="saving" @click="close">×</button></header>
    <form class="report-edit-form" @submit.prevent="save"><div class="business-body"><div v-if="error" class="error" role="alert">{{error}}</div>
      <div class="form-grid business-editor">
        <label>归属客户档案<select v-model="form.customerId" :disabled="saving"><option :value="null">暂不归属（保留原表客户文字）</option><option v-for="c in customers" :key="c.id" :value="c.id">{{c.fullName}}</option></select></label>
        <label>报告分类<select v-model="form.category" :disabled="saving"><option>开发</option><option>成交</option><option value="EOL">EOL（生命周期结束）</option></select></label>
        <label v-for="[key,label] in reportFields" :key="key" :class="{wide:['statusNote','notes'].includes(key)}">{{label}}
          <textarea v-if="['statusNote','notes'].includes(key)" v-model.trim="form.fields[key]" rows="3" maxlength="2000" :disabled="saving"></textarea>
          <input v-else v-model.trim="form.fields[key]" :required="key==='projectName'" :maxlength="['reportDate','expectedMpText'].includes(key)?100:255" :inputmode="['quotePrice','estimatedAnnualQuantity','estimatedAnnualRevenue','competitorPrice'].includes(key)?'decimal':'text'" :disabled="saving||(key==='customerName'&&!!form.customerId)" :placeholder="key==='customerName'&&form.customerId?'使用所选客户档案的公司全称':undefined">
        </label>
        <label>币种<input v-model.trim="form.currency" maxlength="30" :disabled="saving" placeholder="如：人民币 / CNY"></label><label>数量单位<input v-model.trim="form.quantityUnit" maxlength="30" :disabled="saving" placeholder="如：件、平方米"></label><label class="wide">计价与含税说明<input v-model.trim="form.priceTerms" maxlength="255" :disabled="saving" placeholder="如：每件含税报价"></label><label class="wide">业务交易阶段<select v-model="form.businessStage" :disabled="saving"><option value="">待确认（留空）</option><option v-for="stage in stages" :key="stage">{{stage}}</option></select></label>
        <label class="report-important wide"><input v-model="form.important" type="checkbox" :disabled="saving">标记为重点项目（独立于开发/成交/EOL分类）</label>
        <p class="muted wide">{{row?.detailId||!row?'单价及预测数值最多13位整数、6位小数；未知留空，说明写入备注。':'旧报告的原始文字可以保留；不会自动拆分、合并或转换成订单。'}} 预估营业额与实际订单、收款分别记录，不自动乘算。修改公司、项目名称、终端或应用将同时更新该项目的其他型号规格。日期和量产时间可保留月份、季度等原精度。</p>
      </div></div><footer class="business-footer"><span>确认的是报告资料，不会自动生成订单或收款。</span><div class="order-footer-actions"><button type="button" class="button" :disabled="saving" @click="close">取消编辑</button><button class="button primary" :disabled="saving">{{saving?'保存中…':'保存报告行'}}</button></div></footer></form>
  </section></div>
</template>
