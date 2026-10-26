"""Default entry rules against disposable H2; no real customer data."""
import unittest
import subprocess
import verify_company_weekly as fixture
from verify_company_weekly import http


class ReportDefaults(unittest.TestCase):
    setUpClass=classmethod(fixture.CompanyWorkflow.setUpClass.__func__)
    tearDownClass=classmethod(fixture.CompanyWorkflow.tearDownClass.__func__)

    def config(self, **values):
        status,current=http('/report/defaults');self.assertEqual(status,200,current)
        body={'revision':current.get('revision'),'fields':{k:{'enabled':True,'value':v} for k,v in values.items()}}
        status,saved=http('/report/defaults',body,'PUT');self.assertEqual(status,200,saved)
        return saved

    def test_a_empty_and_validation_and_stale_settings(self):
        status,empty=http('/report/defaults');self.assertEqual(status,200,empty)
        self.assertTrue(all(not v['enabled'] and v['value']=='' for v in empty['fields'].values()))
        before=http('/activities')[1]['total']
        current=self.config(owner='合成经办人',brand='合成品牌')
        self.assertEqual(http('/activities')[1]['total'],before)
        self.assertEqual(http('/report/defaults',{'revision':empty.get('revision'),'fields':{}},'PUT')[0],409)
        for key,value in [('owner','x'*256),('currency','x'*31),('projectName','不允许固定'),('brand','A\x00B')]:
            body={'revision':current['revision'],'fields':{key:{'enabled':True,'value':value}}}
            self.assertEqual(http('/report/defaults',body,'PUT')[0],400)
        self.assertEqual(http('/report/defaults',{'revision':current['revision'],'fields':{'owner':{'enabled':True,'value':''}}},'PUT')[0],400)

    def test_defaults_only_fill_omitted_new_fields_and_brand_is_preserved(self):
        self.config(owner='合成经办人',brand='合成品牌',currency='CNY',quantityUnit='件')
        status,row=http('/report/rows',{'category':'开发','fields':{'projectName':'合成默认报告','materialModel':'DEF-A'}})
        self.assertEqual(status,201,row)
        self.assertEqual((row['fields']['owner'],row['fields']['brand'],row['currency']),('合成经办人','合成品牌','CNY'))
        details=http(f"/projects/{row['projectId']}/details")[1]
        self.assertEqual(details[0]['brand'],'合成品牌')
        # A different current setting must never rewrite an existing row.
        self.config(owner='另一经办人',brand='另一品牌',currency='USD')
        status,updated=http('/report/rows/'+str(row['projectId']),{**row,'fields':{**row['fields'],'owner':'','brand':''},'currency':''},'PUT')
        self.assertEqual(status,200,updated)
        self.assertEqual((updated['fields']['owner'],updated['fields']['brand'],updated['currency']),('','',''))
        status,blank=http('/report/rows',{'category':'开发','fields':{'projectName':'合成主动留空','owner':'','brand':''},'currency':''})
        self.assertEqual(status,201,blank)
        self.assertEqual((blank['fields']['owner'],blank['fields']['brand'],blank['currency']),('','',''))
        self.config()
        status,disabled=http('/report/rows',{'category':'开发','fields':{'projectName':'合成停用默认'}})
        self.assertEqual(status,201,disabled);self.assertEqual(disabled['fields']['owner'],'')

    def test_z_restart_preserves_defaults_and_report_brand(self):
        self.config(owner='合成重启经办人',brand='合成重启品牌')
        status,row=http('/report/rows',{'category':'开发','fields':{'projectName':'合成无型号品牌'}})
        self.assertEqual(status,201,row)
        cls=type(self);command=cls.process.args
        cls.process.terminate();cls.process.wait(timeout=15)
        cls.log.seek(0);cls.log.truncate()
        cls.process=subprocess.Popen(command,stdout=cls.log,stderr=cls.log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        fixture.CompanyWorkflow.wait_ready.__func__(cls)
        self.assertEqual(http('/report/defaults')[1]['fields']['brand']['value'],'合成重启品牌')
        actual=next(r for r in http('/report/rows')[1] if r['projectId']==row['projectId'])
        self.assertEqual(actual['fields']['brand'],'合成重启品牌')

if __name__=='__main__':unittest.main(argv=[__file__]+fixture.rest)
