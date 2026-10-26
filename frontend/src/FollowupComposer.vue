<script setup>
import { reactive } from 'vue'
const props = defineProps({ details: Array, stages: Array, saving: Boolean })
const emit = defineEmits(['save','cancel'])
const form = reactive({ detailId: null, contactDate: '', content: '', source: '', nextAction: '', nextContactDate: '', newBusinessStage: '' })
function submit() { emit('save', { ...form, newBusinessStage: form.detailId ? form.newBusinessStage : '', nextContactDate: form.nextContactDate || null }) }
</script>
<template>
  <form class="form-grid business-editor" @submit.prevent="submit">
    <div class="wide customer-section-heading"><h3>新增业务跟进</h3><p class="muted">按发生日期追加，旧记录保留。若需修正历史内容，请新增更正说明并写明原记录。</p></div>
    <label>关联对象<select v-model="form.detailId" :disabled="saving" @change="form.newBusinessStage = ''"><option :value="null">项目整体</option><option v-for="row in details.filter(d => !d.archived)" :key="row.id" :value="row.id">{{ row.materialModel || '型号待补' }} / {{ row.specification || '规格待补' }}</option></select></label>
    <label>跟进发生日期<input v-model="form.contactDate" type="date" required :disabled="saving"></label>
    <label v-if="form.detailId" class="wide">同步更新该明细的业务阶段<select v-model="form.newBusinessStage" :disabled="saving"><option value="">保留当前阶段</option><option v-for="stage in stages" :key="stage" :value="stage">{{ stage }}</option></select><span class="field-hint">只有明确选择后才更新；项目测试阶段保持原值。</span></label>
    <label class="wide">跟进内容<textarea v-model.trim="form.content" rows="4" maxlength="4000" required :disabled="saving"></textarea></label>
    <label class="wide">资料来源<input v-model.trim="form.source" maxlength="1000" required placeholder="例如：电话沟通、客户邮件、聊天截图及对应日期" :disabled="saving"></label>
    <label class="wide">下一步计划<textarea v-model.trim="form.nextAction" rows="2" maxlength="2000" :disabled="saving"></textarea></label>
    <label>下次跟进日期<input v-model="form.nextContactDate" type="date" :disabled="saving"></label>
    <p class="muted wide">这里只记录来源说明，尚未保存截图附件。跟进内容中的下单意向不会自动生成订单。</p>
    <div class="form-actions"><button type="button" class="button" :disabled="saving" @click="emit('cancel')">取消跟进</button><button class="button primary" :disabled="saving">{{ saving ? '保存中…' : '保存跟进记录' }}</button></div>
  </form>
</template>
