<script setup>
import { computed, ref, watch } from 'vue'
import { frozenReportColumns } from './report-fields'
import {visibleReportFields,readDrawer,saveDrawer} from './report-preferences'
const props=defineProps({rows:Array,projects:Array,selectedIds:Array,busy:Boolean})
const emit=defineEmits(['edit','business','basic','priority','remove','select','select-visible','clear-selection','defaults'])
const category=ref('全部')
const identityExpanded=ref(readDrawer())
const columns=computed(()=>visibleReportFields(identityExpanded.value))
function toggleIdentity(){identityExpanded.value=!identityExpanded.value;saveDrawer(identityExpanded.value);if(tableWrap.value)tableWrap.value.scrollLeft=0}
const tableWrap=ref(null)
function showMoney(){const wrap=tableWrap.value,target=wrap?.querySelector('[data-report-key="quotePrice"]');if(!target)return;const fixed=[...wrap.querySelectorAll('thead .project-frozen')].reduce((n,e)=>n+e.getBoundingClientRect().width,0);wrap.scrollTo({left:wrap.scrollLeft+target.getBoundingClientRect().left-wrap.getBoundingClientRect().left-fixed,behavior:'auto'})}
const visible=computed(()=>props.rows.filter(r=>category.value==='全部'||(category.value==='重点项目'?r.important:r.category===category.value)))
const ids=computed(()=>[...new Set(visible.value.map(r=>r.projectId))])
const allSelected=computed(()=>ids.value.length>0&&ids.value.every(id=>props.selectedIds.includes(id)))
const partial=computed(()=>!allSelected.value&&ids.value.some(id=>props.selectedIds.includes(id)))
const project=r=>props.projects.find(p=>p.id===r.projectId)
const scrollWidth=visibleReportFields(true).filter(([key])=>!frozenReportColumns[key]).reduce((sum,[,,width])=>sum+width,0)+340
watch(category,()=>emit('clear-selection'))
</script>
<template>
  <div class="report-category-tabs" aria-label="项目报告分类"><button v-for="name in ['全部','开发','成交','EOL','重点项目']" :key="name" :class="{active:category===name}" :aria-pressed="category===name" :disabled="busy" @click="category=name">{{name==='EOL'?'EOL（生命周期结束）':name}}</button><button title="将主表滚动到单价、预估年用量和预估年营业额" @click="showMoney">查看金额列 →</button><span>{{visible.length}} 条型号规格 / {{ids.length}} 个项目</span></div>
  <div class="report-drawer-bar"><button class="report-drawer-toggle" :aria-expanded="identityExpanded" aria-controls="reportTable" @click="toggleIdentity">{{identityExpanded?'◀ 收起信息栏':'▶ 展开信息栏'}}</button><span class="muted">{{identityExpanded?'采购公司 · 项目名称 · 终端客户':'信息栏已收起，展开可查看公司与项目名称'}}</span><button class="text-button" @click="emit('defaults')">默认填入设置</button></div>
  <p class="report-ledger-help">单价、预估年用量和预估年营业额直接在主表查看；向右拖动查看其余字段。每个型号规格一行，原表资料未自动合并。预估营业额不代表订单或收款。</p>
  <div ref="tableWrap" class="table-wrap project-table-wrap" :class="{'identity-collapsed':!identityExpanded}"><table id="reportTable" class="projects-table report-table" :style="{'--report-scroll-width':scrollWidth+'px'}"><colgroup><col class="selection-column"><col v-for="[key,,width] in columns" :key="key" :class="frozenReportColumns[key]" :style="frozenReportColumns[key]?undefined:{width:width+'px'}"><col style="width:340px"></colgroup>
    <thead><tr><th class="selection-column project-frozen"><input class="project-checkbox" type="checkbox" aria-label="全选当前报告显示的项目" :checked="allSelected" :indeterminate="partial" :disabled="busy||!ids.length" @change="emit('select-visible',ids,$event.target.checked)"></th><th v-for="[key,label] in columns" :key="key" :data-report-key="key" :class="frozenReportColumns[key]">{{label}}</th><th>操作</th></tr></thead>
    <tbody><tr v-for="row in visible" :key="row.key"><td class="selection-column project-frozen"><div class="report-select-edit"><input class="project-checkbox" type="checkbox" :aria-label="`选择项目 ${row.fields.projectName}`" :checked="selectedIds.includes(row.projectId)" :disabled="busy" @change="emit('select',row.projectId,$event.target.checked)"><button class="report-inline-edit" aria-label="编辑报告行" :disabled="busy||row.archivedOnly" :title="row.archivedOnly?'请先在规格与跟进中恢复明细':`编辑项目：${row.fields.projectName}`" @click="emit('edit',row)">编辑</button></div></td>
      <td v-for="[key] in columns" :key="key" :class="[frozenReportColumns[key],{'report-long-text':['statusNote','notes'].includes(key)}]" :title="row.fields[key]||undefined">
        <strong v-if="key==='projectName'||['quotePrice','estimatedAnnualRevenue'].includes(key)">{{row.fields[key]||'—'}}</strong><span v-else>{{row.fields[key]||'—'}}</span>
        <small v-if="key==='projectName'&&row.archivedOnly" class="muted">明细全部归档 · 可进入恢复</small>
        <small v-if="key==='customerName'&&!row.customerId" class="muted">{{row.fields.customerName?'原表客户 · 未建档归属':'未归属客户'}}</small>
        <small v-if="key==='quotePrice'&&(row.currency||row.quantityUnit||row.priceTerms)" class="muted">{{[row.currency,row.quantityUnit,row.priceTerms].filter(Boolean).join(' · ')}}</small>
        <small v-if="key==='estimatedAnnualRevenue'&&row.currency" class="muted">{{row.currency}}</small>
      </td><td class="report-row-actions"><button class="text-button priority-toggle" :class="{'is-important':row.important}" :aria-pressed="row.important" :disabled="busy" @click="emit('priority',project(row))">{{row.important?'★ 取消重点':'☆ 标记重点'}}</button><button class="text-button" :disabled="busy" @click="emit('business',project(row))">规格与跟进</button><button class="text-button" :disabled="busy" @click="emit('basic',project(row))">项目基础资料</button><button class="text-button danger" :disabled="busy" @click="emit('remove',project(row))">删除项目</button></td>
    </tr><tr v-if="!visible.length"><td class="empty" :colspan="columns.length+2"><strong>当前范围暂无报告行</strong><span>可新建项目报告行，或导入已经填写的项目开发表。</span></td></tr></tbody>
  </table></div>
</template>
