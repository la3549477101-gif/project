<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { api } from './api'
import SalesOrderForm from './SalesOrderForm.vue'
import SalesOrderSummary from './SalesOrderSummary.vue'
const props = defineProps({ customers:Array, projects:Array, customerId:Number, revision:Number })
const emit = defineEmits(['changed'])
const selected = ref('')
const page = ref(0)
const data = ref({items:[],total:0,totals:[]})
const loading = ref(false)
const error = ref('')
const creating = ref(false)
const opened = ref(null)
const opening = ref(false)
const scopeId = computed(() => props.customerId || (selected.value ? Number(selected.value) : null))
let requestId = 0
let detailToken = 0
async function load() {
  const token = ++requestId; loading.value = true; error.value = ''; data.value = {items:[],total:0,totals:[]}
  try { const result = await api.orders({customerId:scopeId.value,page:page.value,size:20}); if (token === requestId) data.value = result }
  catch (err) { if (token === requestId) error.value = err.message }
  finally { if (token === requestId) loading.value = false }
}
watch([selected,() => props.customerId,() => props.revision], () => { if (page.value) page.value = 0; else load() })
watch(page,load)
load()
onUnmounted(() => { requestId++; detailToken++ })
async function open(id) {
  const token = ++detailToken; opening.value = true; error.value = ''
  try { const row = await api.order(id); if (token === detailToken) opened.value = row }
  catch (err) { if (token === detailToken) error.value = err.message }
  finally { if (token === detailToken) opening.value = false }
}
function saved(order) { creating.value = false; opened.value = order; emit('changed') }
</script>
<template>
  <section class="panel orders-workspace">
    <div class="panel-heading"><div><span class="section-index">订单 / 含税金额</span><h2>{{ customerId ? '该客户订单与累计金额' : '全部订单' }}</h2><p class="muted">每笔采购单独记录，客户条件按下单时保存；累计金额不是已收款。</p></div><button class="button primary" :disabled="!customers.length" @click="creating = true">＋ 新建订单</button></div>
    <div class="toolbar"><label v-if="!customerId" class="inline-label">客户<select v-model="selected" class="field" aria-label="筛选订单所属客户"><option value="">全部客户</option><option v-for="c in customers" :key="c.id" :value="String(c.id)">{{ c.fullName }}</option></select></label><span class="count">共 {{ data.total }} 笔订单</span><div class="order-toolbar-actions"><button class="button" :disabled="loading" @click="load">刷新订单</button><a class="button" :href="api.orderExportUrl(scopeId)" title="导出当前客户范围的全部订单明细，格式CSV（逗号分隔值）">导出订单数据</a></div></div>
    <div v-if="error" class="error" role="alert">{{ error }}</div>
    <div class="order-totals"><article v-for="total in data.totals" :key="total.currency"><span>{{ scopeId ? '客户累计订单金额' : '累计订单金额' }} · {{ total.currency }}</span><strong>{{ total.amount }}</strong><small>{{ total.orderCount }} 笔 · 含税 · 全部匹配订单</small></article><p v-if="!data.totals.length" class="muted">{{ loading ? '正在读取订单汇总…' : '暂无订单金额；不同币种将分别累计。' }}</p></div>
    <div class="order-table-wrap"><table class="orders-table"><thead><tr><th>内部订单号 / 客户订单号</th><th>客户</th><th>下单日期 / 用途</th><th>含税总额</th><th>明细</th><th>操作</th></tr></thead><tbody><tr v-for="order in data.items" :key="order.id"><td><strong>{{ order.internalNumber }}</strong><small>{{ order.customerOrderNo || '客户订单号未提供' }}</small></td><td>{{ order.customerName }}</td><td><span>{{ order.orderDate }}</span><small>{{ order.purpose === 'SAMPLE' ? '样品单' : '量产单' }}</small></td><td><strong>{{ order.totalAmount }} {{ order.currency }}</strong></td><td>{{ order.lineCount }} 项型号规格</td><td><button class="text-button" :disabled="opening" @click="open(order.id)">查看订单</button></td></tr><tr v-if="!data.items.length"><td colspan="6" class="business-empty">{{ loading ? '正在读取订单…' : '暂无订单。请在采购事实确认后新建；项目报价及下单意向不会自动生成订单。' }}</td></tr></tbody></table></div>
    <footer class="footer"><span>按下单日期倒序；不同币种不混加，不自动推算交货或收款。</span><div class="activity-pager"><button class="button" :disabled="loading || page === 0" @click="page--">上一页</button><span>第 {{ page + 1 }} 页</span><button class="button" :disabled="loading || (page + 1) * 20 >= data.total" @click="page++">下一页</button></div></footer>
  </section>
  <SalesOrderForm v-if="creating" :customers="customers" :projects="projects" :default-customer-id="scopeId" @close="creating = false" @saved="saved" />
  <div v-if="opened" class="overlay business-overlay" @click.self="opened = null" @keydown.esc="opened = null"><section class="modal business-modal" role="dialog" aria-modal="true" aria-labelledby="orderViewTitle"><header class="modal-head"><h2 id="orderViewTitle">订单详情 · {{ opened.internalNumber }}</h2><button class="close" aria-label="关闭订单详情" @click="opened = null">×</button></header><div class="business-body"><SalesOrderSummary :order="opened" /></div><footer class="business-footer"><span>历史订单按保存时的客户和产品资料展示。</span><button class="button" @click="opened = null">关闭订单详情</button></footer></section></div>
</template>
