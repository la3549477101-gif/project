<script setup>
import { computed } from 'vue'
const props = defineProps({ customer: { type: Object, required: true }, groups: { type: Array, default: () => [] } })
const filledCount = group => group.fields.filter(f => props.customer.profile?.[f.key]).length
const totalFilled = computed(() => props.groups.reduce((n, g) => n + filledCount(g), 0))
const totalFields = computed(() => props.groups.reduce((n, g) => n + g.fields.length, 0))
</script>
<template>
  <div class="customer-profile-groups">
    <p class="muted profile-completion">备案资料 {{ totalFilled }} / {{ totalFields }} 项已填 · 未填写的信息保持待补充</p>
    <details v-for="group in groups" :key="`${customer.id}-${group.key}`" class="customer-profile-group" :open="group.key === 'terms' || group.key === 'billing'">
      <summary><span>{{ group.title }}</span><small>{{ filledCount(group) }} / {{ group.fields.length }}</small></summary>
      <p class="muted">{{ group.hint }}</p>
      <dl class="customer-facts"><div v-for="field in group.fields" :key="field.key" :class="{ wide: field.type === 'textarea' }"><dt>{{ field.label }}</dt><dd :class="{ 'is-missing': !customer.profile?.[field.key] }">{{ customer.profile?.[field.key] || '待补充' }}</dd></div></dl>
    </details>
  </div>
</template>
