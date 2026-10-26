<script setup>
defineProps({ order: { type:Object, required:true } })
const terms = {ourCompany:'我司交易抬头',tradeMethod:'交易方式',paymentCondition:'收款条件',creditLimit:'信用额度',extraTerms:'其他交易约定',reconciliationCycle:'对账周期',reconciliationDate:'对账日期规则',invoiceDate:'开票日期规则',taxIncluded:'客户档案含税约定'}
</script>
<template>
  <div class="order-summary">
    <div class="order-total-banner"><div><small>{{ order.id ? order.internalNumber : '订单核对预览 · 尚未保存' }}</small><h3>{{ order.customerName }}</h3><p>{{ order.orderDate }} · {{ order.purpose === 'SAMPLE' ? '样品单' : '量产单' }} · 客户订单号：{{ order.customerOrderNo || '未提供' }}</p></div><div><span>订单含税总额</span><strong>{{ order.totalAmount }} <small>{{ order.currency }}</small></strong></div></div>
    <p class="muted">每行数量 × 含税成交单价，四舍五入保留2位后合计。各行单位按录入值保存，不自动换算。</p>
    <div class="order-table-wrap"><table class="order-lines-table"><thead><tr><th>项目 / 型号 / 规格</th><th>本次数量</th><th>含税成交单价</th><th>明细含税金额</th><th>约定交期</th></tr></thead><tbody><tr v-for="(line,index) in order.lines" :key="line.id || index"><td><strong>{{ line.materialModel || '型号待补' }}</strong><span>{{ line.specification || '规格待补' }}</span><small>{{ line.projectName }}</small><p v-if="line.notes">{{ line.notes }}</p></td><td>{{ line.quantity }} {{ line.unit }}</td><td>{{ line.unitPrice }} {{ order.currency }}/{{ line.unit }}</td><td>{{ line.amount }} {{ order.currency }}</td><td>{{ line.expectedDeliveryDate || '待确认' }}</td></tr></tbody></table></div>
    <dl class="order-basic-facts"><div><dt>已确认采购的订单依据</dt><dd>{{ order.source }}</dd></div><div v-if="order.notes"><dt>订单备注</dt><dd>{{ order.notes }}</dd></div></dl>
    <details class="order-terms" open><summary>客户交易条件{{ order.id ? '历史快照' : '（本次保存时会建立快照）' }}</summary><p class="muted">后续修改客户档案不追溯改变本订单。客户档案约定与本单含税价不一致时，请在订单依据中说明真实约定。</p><dl class="customer-facts"><div v-for="(label,key) in terms" :key="key"><dt>{{ label }}</dt><dd>{{ order.termsSnapshot?.[key] || '未提供' }}</dd></div></dl></details>
    <p class="notice order-notice">此处记录订单金额，不表示已经交货或收款。交货和收款记录将在后续接入。</p>
  </div>
</template>
