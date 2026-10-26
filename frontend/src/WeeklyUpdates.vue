<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { api } from './api'
const props = defineProps({ customers: { type: Array, default: () => [] }, customerId: Number, scope: { type: String, default: 'week' }, existingProjectIds: { type: Array, default: () => [] }, revision: Number })
const emit = defineEmits(['open-project','open-customer'])
const selected = ref(props.customerId ? String(props.customerId) : '')
const page = ref(0)
const data = ref({ items: [], total: 0 })
const error = ref('')
const loading = ref(false)
let requestId = 0
const stamp = value => new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
const day = value => new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', dateStyle: 'medium' }).format(new Date(value))
const weekRange = computed(() => data.value.from && props.scope === 'week' ? day(data.value.from) + ' 至 ' + day(new Date(new Date(data.value.to).getTime() - 1)) + ' · 北京时间' : '')
async function load() {
  const token = ++requestId
  loading.value = true; error.value = ''; data.value = { items: [], total: 0 }
  try {
    const result = await api.activities({ scope: props.scope, customerId: props.customerId || selected.value || null, page: page.value, size: 25 })
    if (token === requestId) data.value = result
  } catch (err) { if (token === requestId) error.value = err.message }
  finally { if (token === requestId) loading.value = false }
}
watch([selected, () => props.customerId, () => props.scope, () => props.revision], () => { if (page.value) page.value = 0; else load() })
watch(page, load)
load()
onUnmounted(() => { requestId++ })
function exists(row) { return row.entityType === 'CUSTOMER' ? props.customers.some(c => c.id === row.customerId) : props.existingProjectIds.includes(row.projectId) }
function open(row) { if (exists(row)) emit(row.entityType === 'CUSTOMER' ? 'open-customer' : 'open-project', row.entityType === 'CUSTOMER' ? row.customerId : row.projectId) }
</script>
<template>
  <section class="panel activity-panel">
    <div class="panel-heading"><div><span class="section-index">动态 / {{ scope === 'week' ? '本周' : '公司' }}</span><h2>{{ scope === 'week' ? '本周更新' : '公司变更记录' }}</h2><p class="muted">{{ weekRange || '按保存时间倒序，保留每次实际修改' }}</p></div><button class="button" :disabled="loading" @click="load">刷新记录</button></div>
    <div class="toolbar"><label v-if="!customerId" class="inline-label">公司<select v-model="selected" class="field" aria-label="筛选更新所属公司"><option value="">全部公司（含未归属项目）</option><option v-for="c in customers" :key="c.id" :value="String(c.id)">{{ c.fullName }}</option></select></label><span class="count">{{ loading ? '加载中…' : '共 ' + data.total + ' 次新增或修改' }}</span></div>
    <div v-if="error" class="error" role="alert">{{ error }}</div>
    <ol class="activity-list"><li v-for="row in data.items" :key="row.id">
      <div class="activity-meta"><span class="change-kind" :class="row.action">{{ row.action === 'NEW' ? '新增' : '修改' }}</span><time :datetime="row.occurredAt">{{ stamp(row.occurredAt) }}</time><span>{{ ({ CUSTOMER: '客户资料', PROJECT: '项目', DETAIL: '型号规格', FOLLOWUP: '业务跟进' })[row.entityType] || '项目' }}</span></div>
      <h3>{{ row.objectName }}</h3><p class="muted">{{ row.customerName || '未归属公司' }}<template v-if="row.previousCustomerId"> · 原公司：{{ row.previousCustomerName }}</template></p><p class="change-detail">{{ row.detail }}</p>
      <button v-if="exists(row)" class="text-button" @click="open(row)">查看{{ row.entityType === 'CUSTOMER' ? '客户' : '项目' }} →</button><span v-else class="muted">记录已删除，保留历史摘要</span>
    </li></ol>
    <div v-if="!data.items.length && !loading && !error" class="empty"><strong>{{ scope === 'week' ? '本周还没有新增或修改' : '暂时没有变更记录' }}</strong><span>旧资料不会被自动算作本周更新；以后保存的实际变化会显示在这里。</span></div>
    <footer class="footer"><span>只记录实际发生的变化</span><div class="activity-pager"><button class="button" :disabled="loading || page === 0" @click="page--">上一页</button><span>第 {{ page + 1 }} 页</span><button class="button" :disabled="loading || (page + 1) * 25 >= data.total" @click="page++">下一页</button></div></footer>
  </section>
</template>
