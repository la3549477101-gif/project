<script setup>
import { reactive } from 'vue'
const props = defineProps({ detail: Object, stages: Array, saving: Boolean })
const emit = defineEmits(['save','cancel'])
const fields = [
  ['materialModel','材料型号'], ['brand','品牌'], ['specification','成品规格'], ['productLine','产品线'], ['owner','负责人'],
  ['reportDate','报告日期（保留原精度）'], ['caseStatus','案子状况（按原约定填写）'],
  ['quotePrice','当前报价','decimal'], ['currency','币种'], ['quantityUnit','数量单位'], ['priceTerms','计价与含税说明'],
  ['estimatedAnnualQuantity','预估年用量','decimal'], ['estimatedAnnualRevenue','预估年营业额（手工填写）','decimal'],
  ['expectedMpText','预估量产时间（支持月份、季度）'], ['competitor','竞争对手'], ['competitorPrice','竞争对手单价','decimal'],
  ['statusNote','当前业务说明','textarea'], ['notes','备注','textarea'],
]
const form = reactive(Object.fromEntries([...fields.map(([key]) => [key, props.detail?.[key] ?? '']), ['businessStage', props.detail?.businessStage || ''], ['reportCategory',props.detail?.reportCategory || '']]))
function submit() {
  const result = { ...form }
  for (const [key,,type] of fields) if (type === 'decimal') result[key] = form[key] === '' ? null : form[key]
  emit('save', result)
}
</script>
<template>
  <form class="form-grid business-editor" @submit.prevent="submit">
    <div class="wide customer-section-heading"><h3>{{ detail ? '编辑型号规格' : '新增型号规格' }}</h3><p class="muted">型号和规格至少填写一项。同一型号不同规格分别保存，报价不代表实际订单成交价。</p></div>
    <label class="wide">业务交易阶段<select v-model="form.businessStage" :disabled="saving"><option value="">待确认（留空）</option><option v-for="stage in stages" :key="stage" :value="stage">{{ stage }}</option></select></label>
    <label class="wide">项目报告分类<select v-model="form.reportCategory" :disabled="saving"><option value="">开发（默认）</option><option>开发</option><option>成交</option><option value="EOL">EOL（生命周期结束）</option></select></label>
    <label v-for="[key,label,type] in fields" :key="key" :class="{ wide: type === 'textarea' }">{{ label }}
      <textarea v-if="type === 'textarea'" v-model.trim="form[key]" rows="3" maxlength="2000" :disabled="saving"></textarea>
      <input v-else v-model.trim="form[key]" :inputmode="type === 'decimal' ? 'decimal' : 'text'" :maxlength="type === 'decimal' ? 30 : key === 'expectedMpText' ? 100 : ['currency','quantityUnit'].includes(key) ? 30 : 255" :disabled="saving">
    </label>
    <p class="muted wide">报价和预测量支持最多13位整数、6位小数；未知请留空。请一并填写币种、数量单位与含税口径，营业额不会自动推算；竞争对手单价须采用相同口径，其他口径请写入备注。</p>
    <div class="form-actions"><button type="button" class="button" :disabled="saving" @click="emit('cancel')">取消编辑</button><button class="button primary" :disabled="saving">{{ saving ? '保存中…' : '保存型号规格' }}</button></div>
  </form>
</template>
