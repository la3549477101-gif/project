<script setup>
import {onMounted,ref} from 'vue'
import {api} from './api'
import {defaultFieldSpecs} from './report-preferences'
const emit=defineEmits(['close','saved'])
const config=ref(null),loading=ref(true),saving=ref(false),error=ref('')
async function load(){loading.value=true;error.value='';try{config.value=await api.reportDefaults()}catch(e){error.value=e.message}finally{loading.value=false}}
async function save(){if(!config.value||saving.value)return;saving.value=true;error.value='';try{const result=await api.saveReportDefaults(config.value);emit('saved',result)}catch(e){error.value=e.message}finally{saving.value=false}}
function close(){if(!saving.value)emit('close')}
onMounted(load)
</script>
<template>
  <div class="overlay business-overlay" @click.self="close" @keydown.esc="close"><section class="modal business-modal report-defaults-dialog" role="dialog" aria-modal="true" aria-labelledby="defaultsTitle">
    <header class="modal-head"><div><h2 id="defaultsTitle">默认填入设置</h2><p class="muted">为新建项目报告预填常用内容，每次录入仍可修改或清空。</p></div><button class="close" aria-label="关闭默认填入设置" :disabled="saving" @click="close">×</button></header>
    <form class="report-edit-form" @submit.prevent="save"><div class="business-body">
      <p v-if="loading" role="status">正在读取设置…</p><div v-if="error" class="error" role="alert">{{error}} <button v-if="!config" type="button" class="text-button" @click="load">重新读取设置</button></div>
      <div v-if="config" class="report-default-options"><div v-for="[key,label,max] in defaultFieldSpecs" :key="key" class="report-default-option">
        <label class="report-default-switch"><input v-model="config.fields[key].enabled" type="checkbox" :disabled="saving" :aria-label="`启用${label}默认填入`">{{label}}</label>
        <label class="report-default-value"><span class="muted">默认内容</span><input v-model.trim="config.fields[key].value" :aria-label="`默认${label}`" :maxlength="max" :required="config.fields[key].enabled" :disabled="saving" :placeholder="`填写常用${label}；勾选后启用`"></label>
      </div></div>
      <p class="muted">设置只影响之后新建的报告，不改已有记录或原表导入内容。停用可保留文字备用。这里不设置客户、项目名称、数量或金额。</p>
    </div><footer class="business-footer"><span>设置保存在本机数据库，重启后保留。</span><div class="order-footer-actions"><button type="button" class="button" :disabled="saving" @click="close">取消设置</button><button class="button primary" :disabled="saving||loading||!config">{{saving?'保存中…':'保存默认设置'}}</button></div></footer></form>
  </section></div>
</template>
