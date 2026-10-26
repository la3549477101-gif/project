<script setup>
import { computed, reactive, ref } from 'vue'
import { api } from './api'
const props = defineProps({ customer: Object, customers: { type: Array, default: () => [] }, groups: { type: Array, default: () => [] } })
const emit = defineEmits(['close','saved'])
const saving = ref(false)
const error = ref('')
const form = reactive(Object.fromEntries(['fullName','shortName','contactName','contactDetails','notes'].map(k => [k, props.customer?.[k] || ''])))
form.profile = { ...props.customer?.profile, ...Object.fromEntries(props.groups.flatMap(g => g.fields.map(f => [f.key, props.customer?.profile?.[f.key] || '']))) }
const activeSection = ref('basic')
const allSections = computed(() => [{ key: 'basic', title: '基本资料' }, ...props.groups])
const filledCount = group => group.fields.filter(f => form.profile[f.key]?.trim()).length
const candidates = computed(() => {
  const name = form.fullName.trim().toLocaleLowerCase()
  return name.length < 2 ? [] : props.customers.filter(c => c.id !== props.customer?.id && [c.fullName,c.shortName].some(v => v && (v.toLocaleLowerCase().includes(name) || name.includes(v.toLocaleLowerCase())))).slice(0,4)
})
function close() { if (!saving.value) emit('close') }
async function save() {
  if (saving.value || !props.groups.length) return
  error.value = ''
  if (!form.fullName.trim()) { activeSection.value = 'basic'; error.value = '请填写公司全称'; return }
  saving.value = true
  try { emit('saved', props.customer ? await api.updateCustomer(props.customer.id, form) : await api.createCustomer(form)) }
  catch (err) { error.value = err.message }
  finally { saving.value = false }
}
</script>
<template>
  <div class="overlay" @click.self="close" @keydown.esc="close">
    <section class="modal customer-editor" role="dialog" aria-modal="true" aria-labelledby="customerTitle">
      <header class="modal-head"><div><h2 id="customerTitle">{{ customer ? '编辑客户资料' : '新建客户公司' }}</h2><p class="muted">填写实际向你采购的公司，终端使用公司在项目内另行记录。</p></div><button class="close" aria-label="关闭" :disabled="saving" @click="close">×</button></header>
      <form class="customer-editor-form" novalidate @submit.prevent="save">
        <div v-if="error" class="error" role="alert">{{ error }}</div>
        <p v-if="!groups.length" class="error" role="alert">客户字段暂未读取成功，请关闭后刷新页面再试。</p>
        <nav class="customer-section-nav" aria-label="客户资料分组"><button v-for="section in allSections" :key="section.key" type="button" :class="{ active: activeSection === section.key }" :aria-pressed="activeSection === section.key" @click="activeSection = section.key">{{ section.title }}</button></nav>
        <div class="customer-editor-body">
        <section v-show="activeSection === 'basic'" class="form-grid customer-field-section" aria-label="基本资料">
        <div class="wide customer-section-heading"><h3>基本资料</h3><p class="muted">公司全称为必填项，其余内容可先留空，后续继续补充。</p></div>
        <label class="wide">公司全称<input v-model.trim="form.fullName" required maxlength="255" autofocus></label>
        <p v-if="candidates.length" class="notice wide">相似的已有客户：{{ candidates.map(c => c.fullName).join('、') }}。请核对，避免重复建档。</p>
        <label>常用简称<input v-model.trim="form.shortName" maxlength="255"></label><label>联系人<input v-model.trim="form.contactName" maxlength="255"></label>
        <label class="wide">联系方式<input v-model.trim="form.contactDetails" maxlength="255"></label><label class="wide">备注<textarea v-model.trim="form.notes" rows="3" maxlength="4000"></textarea></label>
        </section>
        <section v-for="group in groups" v-show="activeSection === group.key" :key="group.key" class="form-grid customer-field-section" :aria-label="group.title">
          <div class="wide customer-section-heading"><h3>{{ group.title }}<small>{{ filledCount(group) }} / {{ group.fields.length }} 项已填</small></h3><p class="muted">{{ group.hint }}</p></div>
          <label v-for="field in group.fields" :key="field.key" :class="{ wide: field.type === 'textarea' }">{{ field.label }}
            <select v-if="field.type === 'select'" v-model="form.profile[field.key]"><option value="">待确认（留空）</option><option v-for="option in field.options" :key="option" :value="option">{{ option }}</option></select>
            <textarea v-else-if="field.type === 'textarea'" v-model.trim="form.profile[field.key]" rows="3" :maxlength="field.maxLength"></textarea>
            <input v-else v-model.trim="form.profile[field.key]" :type="field.type" :maxlength="field.maxLength">
            <span v-if="field.hint" class="field-hint">{{ field.hint }}</span>
          </label>
        </section>
        </div>
        <footer class="customer-editor-footer"><p class="muted">{{ customer ? '保存所有分组的修改，保留原有客户文件夹位置。' : '保存所有分组，成功后自动建立桌面客户文件夹；创建失败可重试。' }}</p><div class="form-actions"><button type="button" class="button" :disabled="saving" @click="close">取消</button><button class="button primary" :disabled="saving || !groups.length">{{ saving ? '保存中…' : '保存客户资料' }}</button></div></footer>
      </form>
    </section>
  </div>
</template>
