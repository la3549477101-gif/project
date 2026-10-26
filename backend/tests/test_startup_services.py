import io
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from serve_frontend import make_server
from launch_runtime import atomic_json
from launch_runtime import RuntimePack


class StaticFrontend(unittest.TestCase):
    def test_compiled_assets_health_and_cache_headers(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'assets').mkdir();(root/'index.html').write_text('<script src="/assets/a.js"></script>',encoding='utf-8');(root/'assets/a.js').write_text('export default 1',encoding='utf-8')
            server=make_server(root,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));base=f'http://127.0.0.1:{server.server_port}'
            try:
                with opener.open(base+'/') as response:self.assertEqual(response.headers['Cache-Control'],'no-store')
                with opener.open(base+'/assets/a.js') as response:
                    self.assertIn('javascript',response.headers['Content-Type']);self.assertIn('immutable',response.headers['Cache-Control']);self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff')
                with opener.open(base+'/__app_health__') as response:self.assertIn(b'odm-tracker-frontend',response.read())
                with self.assertRaises(urllib.error.HTTPError) as error:opener.open(base+'/assets/missing.js')
                self.assertEqual(error.exception.code,404)
            finally:server.shutdown();server.server_close();thread.join(timeout=5)


@unittest.skipUnless(os.name=='nt','Windows launcher')
class WindowsLauncher(unittest.TestCase):
    def setUp(self):
        import manage
        self.manage=manage;self.temp=tempfile.TemporaryDirectory();self.logs=Path(self.temp.name)
        self.patchLogs=patch.object(manage,'LOGS',self.logs);self.patchState=patch.object(manage,'STATE',self.logs/'services.json');self.patchLogs.start();self.patchState.start()
    def tearDown(self):self.patchState.stop();self.patchLogs.stop();self.temp.cleanup()
    def test_double_start_lock_rejects_overlap_and_releases(self):
        with self.manage.operation_lock():
            with self.assertRaises(RuntimeError):
                with self.manage.operation_lock():pass
        with self.manage.operation_lock():pass
    def test_atomic_state_and_bad_schema_are_handled(self):
        rows=[{'Name':'springboot','ProcessId':123,'StartedUtcTicks':'456'}]
        atomic_json(self.manage.STATE,rows);self.assertEqual(self.manage.read_state(),rows)
        atomic_json(self.manage.STATE,{'Name':'unknown'})
        with self.assertRaises(RuntimeError):self.manage.read_state()
    def test_reused_pid_is_never_stopped(self):
        command=self.manage.specs()['springboot'][0][0]
        with patch.object(self.manage,'identity',return_value=('999',os.path.normcase(os.path.abspath(command)))):
            with self.assertRaises(RuntimeError):self.manage.matches({'Name':'springboot','ProcessId':123,'StartedUtcTicks':'456'})
    def test_health_checks_do_not_accept_only_a_healthy_backend(self):
        responses=[io.BytesIO(b'{"databaseWritable":true}'),urllib.error.URLError('flask unavailable')]
        with patch.object(self.manage.HTTP,'open',side_effect=responses):
            ok,message=self.manage.healthy();self.assertFalse(ok);self.assertIn('flask',message)
    def test_failed_candidate_retries_last_healthy_runtime_once(self):
        candidate=RuntimePack(self.logs/'new.jar',self.logs/'new-front')
        previous=RuntimePack(self.logs/'old.jar',self.logs/'old-front')
        with patch.object(self.manage,'previous_runtime',return_value=previous), patch.object(self.manage,'launch_runtime',side_effect=[RuntimeError('candidate failed'),None]) as launch:
            self.manage.launch_with_recovery(candidate)
            self.assertEqual([call.args[0] for call in launch.call_args_list],[candidate,previous])
    def test_failed_recovery_does_not_loop(self):
        candidate=RuntimePack(self.logs/'new.jar',self.logs/'new-front')
        previous=RuntimePack(self.logs/'old.jar',self.logs/'old-front')
        with patch.object(self.manage,'previous_runtime',return_value=previous), patch.object(self.manage,'launch_runtime',side_effect=RuntimeError('failed')) as launch:
            with self.assertRaises(RuntimeError):self.manage.launch_with_recovery(candidate)
            self.assertEqual(launch.call_count,2)
    def test_same_failed_runtime_is_not_retried(self):
        candidate=RuntimePack(self.logs/'new.jar',self.logs/'new-front')
        with patch.object(self.manage,'previous_runtime',return_value=candidate), patch.object(self.manage,'launch_runtime',side_effect=RuntimeError('failed')) as launch:
            with self.assertRaises(RuntimeError):self.manage.launch_with_recovery(candidate)
            self.assertEqual(launch.call_count,1)
