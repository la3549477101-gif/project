import {reportFields, displayedReportFields, frozenReportColumns} from './report-fields.js'

export const defaultFieldSpecs=[['owner','负责人',255],['brand','品牌',255],['productLine','产品线',255],['currency','币种',30],['quantityUnit','数量单位',30],['priceTerms','计价与含税说明',255]]
export function initialReportForm(row,config,customerId) {
  const form={...row,fields:Object.fromEntries(reportFields.map(([key])=>[key,row?.fields?.[key]??''])),customerId:row?.customerId??customerId??null,category:row?.category||'开发',important:row?.important||false,currency:row?.currency||'',quantityUnit:row?.quantityUnit||'',priceTerms:row?.priceTerms||'',businessStage:row?.businessStage||''}
  if(!row)for(const [key] of defaultFieldSpecs)if(config?.fields?.[key]?.enabled) {
    if(['currency','quantityUnit','priceTerms'].includes(key))form[key]=config.fields[key].value
    else form.fields[key]=config.fields[key].value
  }
  return form
}
export const visibleReportFields=expanded=>displayedReportFields.filter(([key])=>expanded||!frozenReportColumns[key])
const drawerKey='odm.report.identity-drawer.v1'
export function readDrawer(storage) {try{return (storage??globalThis.localStorage)?.getItem(drawerKey)!=='closed'}catch{return true}}
export function saveDrawer(expanded,storage) {try{(storage??globalThis.localStorage)?.setItem(drawerKey,expanded?'open':'closed')}catch{/* Browser storage is optional. */}}
