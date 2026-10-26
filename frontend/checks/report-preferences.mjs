import assert from 'node:assert/strict'
import {initialReportForm, visibleReportFields, readDrawer, saveDrawer} from '../src/report-preferences.js'
const config={fields:{owner:{enabled:true,value:'合成负责人'},brand:{enabled:true,value:'合成品牌'},currency:{enabled:true,value:'CNY'},productLine:{enabled:false,value:'关闭的默认值'}}}
const fresh=initialReportForm(null,config,null)
assert.equal(fresh.fields.owner,'合成负责人');assert.equal(fresh.fields.brand,'合成品牌');assert.equal(fresh.currency,'CNY');assert.equal(fresh.fields.productLine,'')
const old=initialReportForm({projectId:1,fields:{owner:'',brand:'原品牌'},currency:''},config,null)
assert.equal(old.fields.owner,'');assert.equal(old.fields.brand,'原品牌');assert.equal(old.currency,'')
assert.ok(visibleReportFields(true).some(([key])=>key==='customerName'))
assert.ok(!visibleReportFields(false).some(([key])=>['customerName','projectName','terminalCustomer'].includes(key)))
assert.ok(visibleReportFields(false).some(([key])=>key==='quotePrice'))
const denied={getItem(){throw Error('denied')},setItem(){throw Error('denied')}}
assert.equal(readDrawer(denied),true);saveDrawer(false,denied)
let value;const storage={getItem(){return value},setItem(k,v){value=v}}
saveDrawer(false,storage);assert.equal(readDrawer(storage),false);saveDrawer(true,storage);assert.equal(readDrawer(storage),true)
console.log('默认预填、旧记录保护、抽屉列及存储降级检查通过')
