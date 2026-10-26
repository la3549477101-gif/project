<script setup>
import { computed, reactive, ref } from 'vue'
import { api } from './api'
const props = defineProps({ customer: Object, customers: { type: Array, default: () => [] } })
const emit = defineEmits(['close','saved'])
const saving = ref(false)
const error = ref('')
const form = reactive(Object.fromEntries(['fullName','shortName','contactName','contactDetails','notes'].map(k => [k, props.customer?.[k] || ''])))
const candidates = computed(() => {
  const name = form.fullName.trim().toLocaleLowerCase()
  return name.length < 2 ? [] : props.customers.filter(c => c.id !== props.customer?.id && [c.fullName,c.shortName].some(v => v && (v.toLocaleLowerCase().includes(name) || name.includes(v.toLocaleLowerCase())))).slice(0,4)
})
function close() { if (!saving.value) emit('close') }
async function save() {
  if (saving.value) return
  error.value = ''
  if (!form.fullName.trim()) { error.value = '请填写公司全称'; return }
  saving.value = true
  try { emit('saved', props.customer ? await api.updateCustomer(props.customer.id, form) : await api.createCustomer(form)) }
  catch (err) { error.value = err.message }
  finally { saving.value = false }
}
</script>
<template>
  <div class="overlay" @click.self="close" @keydown.esc="close">
    <section class="modal" role="dialog" aria-modal="true" aria-labelledby="customerTitle">
      <header class="modal-head"><div><h2 id="customerTitle">{{ customer ? '编辑客户资料' : '新建客户公司' }}</h2><p class="muted">填写实际向你采购的公司，终端使用公司在项目内另行记录。</p></div><button class="close" aria-label="关闭" :disabled="saving" @click="close">×</button></header>
      <form class="form-grid" @submit.prevent="save">
        <div v-if="error" class="error wide" role="alert">{{ error }}</div>
        <label class="wide">公司全称<input v-model.trim="form.fullName" required maxlength="255" autofocus></label>
        <p v-if="candidates.length" class="notice wide">相似的已有客户：{{ candidates.map(c => c.fullName).join('、') }}。请核对，避免重复建档。</p>
        <label>常用简称<input v-model.trim="form.shortName" maxlength="255"></label><label>联系人<input v-model.trim="form.contactName" maxlength="255"></label>
        <label class="wide">联系方式<input v-model.trim="form.contactDetails" maxlength="255"></label><label class="wide">备注<textarea v-model.trim="form.notes" rows="3" maxlength="4000"></textarea></label>
        <p class="muted wide">{{ customer ? '公司改名后保留原有客户文件夹位置。' : '保存成功后自动建立桌面客户文件夹；如创建失败，可在客户页面重试。' }}</p>
        <div class="form-actions"><button type="button" class="button" :disabled="saving" @click="close">取消</button><button class="button primary" :disabled="saving">{{ saving ? '保存中…' : '保存客户' }}</button></div>
      </form>
    </section>
  </div>
</template>
