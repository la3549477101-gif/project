export const reportFields = [
  ['owner','负责人',110],['reportDate','日期',130],['productLine','产品线',120],['caseStatus','案子状况',110],
  ['customerName','采购客户公司'],['terminalCustomer','终端客户'],['projectName','项目名称'],['application','应用',150],
  ['materialModel','材料型号',170],['specification','成品规格',200],['quotePrice','单价',150],
  ['estimatedAnnualQuantity','预估年用量',150],['estimatedAnnualRevenue','预估年营业额',160],
  ['statusNote','项目状态',280],['expectedMpText','预估量产时间',150],['competitor','竞争对手',150],['competitorPrice','竞争对手单价',150],['notes','备注',240],
]
export const frozenReportColumns = {customerName:'project-frozen project-company-column',projectName:'project-frozen project-name-column',terminalCustomer:'project-frozen project-terminal-column'}
export const displayedReportFields = [...['customerName','projectName','terminalCustomer'].map(key=>reportFields.find(f=>f[0]===key)),...reportFields.filter(([key])=>!frozenReportColumns[key])]
