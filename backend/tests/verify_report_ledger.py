"""Report table and atomic edits against disposable H2, never the real database."""
import json
import unittest
import verify_company_weekly as fixture
from verify_company_weekly import http


class ReportLedger(unittest.TestCase):
    setUpClass=classmethod(fixture.CompanyWorkflow.setUpClass.__func__)
    tearDownClass=classmethod(fixture.CompanyWorkflow.tearDownClass.__func__)
    def test_report_rows_keep_legacy_fields_and_edit_without_creating_orders(self):
        raw = {'sheet':'开发','file':'synthetic.xls','row':3,'unknown':'keep', 'fields':{
            '负责人':'合成负责人','日期':'2026-10-26','客户':'原表合成客户','项目名称':'合成报告',
            '单价（含税）元':'0.335','预估年营业额':'10000','预估年用量':'待确认','材料型号':'M-A',
            '成品规格':'10x20','项目状态':'样品已下单，等待测试','额外资料':'必须保留'}}
        _,p=http('/projects',{'projectName':'合成报告','reportData':json.dumps(raw,ensure_ascii=False)})
        status,rows=http('/report/rows');self.assertEqual(status,200)
        row=next(r for r in rows if r['projectId']==p['id'])
        self.assertEqual(row['fields']['quotePrice'],'0.335')
        self.assertEqual(row['fields']['estimatedAnnualRevenue'],'10000')
        fields={**row['fields'],'quotePrice':'0.445','statusNote':'已沟通新报价','expectedMpText':'2027年Q1'}
        body={**row,'fields':fields}
        status,saved=http('/report/rows/'+str(p['id']),body,'PUT');self.assertEqual(status,200,saved)
        self.assertEqual(saved['fields']['quotePrice'],'0.445')
        _,projects=http('/projects');record=next(r for r in projects if r['id']==p['id'])
        metadata=json.loads(record['reportData'])
        self.assertEqual(metadata['unknown'],'keep')
        self.assertEqual(metadata['fields']['额外资料'],'必须保留')
        self.assertEqual(metadata['fields']['预估量产时间'],'2027年Q1')
        self.assertEqual(http('/orders')[1]['total'],0)
        self.assertEqual(http('/report/rows/'+str(p['id']),body,'PUT')[0],409)

    def test_structured_specs_are_separate_rows_and_edit_is_atomic(self):
        _,p=http('/projects',{'projectName':'合成多规格'})
        _,a=http(f"/projects/{p['id']}/details",{'materialModel':'M-A','quotePrice':'0.335','notes':'原备注'})
        _,b=http(f"/projects/{p['id']}/details",{'materialModel':'M-B','quotePrice':'1.005'})
        status,rows=http('/report/rows');self.assertEqual(status,200)
        own=[r for r in rows if r['projectId']==p['id']];self.assertEqual(len(own),2)
        row=next(r for r in own if r['detailId']==a['id'])
        body={**row,'fields':{**row['fields'],'projectName':'不能部分改名','quotePrice':'not-a-number'}}
        self.assertEqual(http('/report/rows/'+str(p['id']),body,'PUT')[0],400)
        self.assertEqual(next(r for r in http('/projects')[1] if r['id']==p['id'])['projectName'],'合成多规格')
        body={**row,'category':'成交','fields':{**row['fields'],'reportDate':'2026年10月','caseStatus':'2','quotePrice':'2.123456'}}
        status,saved=http('/report/rows/'+str(p['id']),body,'PUT');self.assertEqual(status,200,saved)
        self.assertEqual(saved['fields']['quotePrice'],'2.123456')
        self.assertEqual(saved['category'],'成交')
        specs=http(f"/projects/{p['id']}/details")[1]
        self.assertEqual(next(r for r in specs if r['id']==a['id'])['notes'],'原备注')
        self.assertEqual(next(r for r in specs if r['id']==b['id'])['quotePrice'],'1.005000')
        archived=http(f"/projects/{p['id']}/details/{a['id']}/archive",{'archived':True})
        self.assertEqual(archived[0],200)
        self.assertEqual(len([r for r in http('/report/rows')[1] if r['projectId']==p['id']]),1)

    def test_archived_only_project_keeps_a_recovery_row(self):
        _,p=http('/projects',{'projectName':'合成归档项目'})
        _,d=http(f"/projects/{p['id']}/details",{'materialModel':'ONLY','quotePrice':'100'})
        http(f"/projects/{p['id']}/details/{d['id']}/archive",{'archived':True})
        own=[r for r in http('/report/rows')[1] if r['projectId']==p['id']]
        self.assertEqual(len(own),1)
        self.assertTrue(own[0]['archivedOnly'])
        self.assertEqual(own[0]['fields']['quotePrice'],'')

    def test_unassigned_customer_text_can_be_changed_on_a_spec_row(self):
        body={'category':'开发','fields':{'projectName':'合成客户文字','customerName':'合成客户A','materialModel':'M-EDIT'}}
        status,created=http('/report/rows',body);self.assertEqual(status,201,created)
        row=next(r for r in http('/report/rows')[1] if r['projectId']==created['projectId'])
        status,updated=http('/report/rows/'+str(row['projectId']),{**row,'fields':{**row['fields'],'customerName':'合成客户B'}},'PUT')
        self.assertEqual(status,200,updated)
        self.assertEqual(updated['fields']['customerName'],'合成客户B')

    def test_unmodeled_report_keeps_currency_unit_and_price_terms(self):
        status,row=http('/report/rows',{'category':'开发','fields':{'projectName':'合成待定型号','quotePrice':'10'},'currency':'USD','quantityUnit':'平方米','priceTerms':'每平方米未税','businessStage':'样品送测'})
        self.assertEqual(status,201,row)
        self.assertEqual((row['currency'],row['quantityUnit'],row['priceTerms']),('USD','平方米','每平方米未税'))
        self.assertEqual(row['businessStage'],'样品送测')
        status,cleared=http('/report/rows/'+str(row['projectId']),{**row,'currency':'','quantityUnit':'','priceTerms':'','businessStage':''},'PUT')
        self.assertEqual(status,200,cleared)
        self.assertEqual((cleared['currency'],cleared['quantityUnit'],cleared['priceTerms'],cleared['businessStage']),('','','',''))


if __name__=='__main__': unittest.main(argv=[__file__]+fixture.rest)
