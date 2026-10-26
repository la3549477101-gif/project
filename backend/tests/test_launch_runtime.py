import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from launch_runtime import prepare_runtime, validate_jar, mark_runtime_ready


class LaunchRuntime(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.jar=self.root/'build/app.jar';self.jar.parent.mkdir()
        with zipfile.ZipFile(self.jar,'w') as z:
            z.writestr('META-INF/MANIFEST.MF','Main-Class: org.springframework.boot.loader.launch.JarLauncher\n')
            z.writestr('BOOT-INF/classes/com/example/odmtracker/OdmTrackerApplication.class',b'class')
            z.writestr('BOOT-INF/lib/example.jar',b'library')
        self.front=self.root/'dist';(self.front/'assets').mkdir(parents=True)
        (self.front/'index.html').write_text('<script type="module" src="/assets/main.js"></script>',encoding='utf-8')
        (self.front/'assets/main.js').write_text('console.log("ready")',encoding='utf-8')
        self.cache=self.root/'runtime'
    def tearDown(self): self.temp.cleanup()
    def test_runtime_is_separate_and_repeated_preparation_is_stable(self):
        first=prepare_runtime(self.jar,self.front,self.cache)
        self.assertNotEqual(first.jar,self.jar)
        self.assertEqual(first.jar.read_bytes(),self.jar.read_bytes())
        self.assertNotEqual(first.frontend,self.front)
        second=prepare_runtime(self.jar,self.front,self.cache)
        self.assertEqual(first.jar,second.jar);self.assertEqual(first.frontend,second.frontend)
        self.jar.write_bytes(b'build-in-progress')
        self.assertTrue(validate_jar(first.jar))
    def test_broken_new_build_falls_back_to_last_valid_snapshot(self):
        first=prepare_runtime(self.jar,self.front,self.cache)
        mark_runtime_ready(first,self.cache)
        self.jar.write_bytes(b'partial')
        fallback=prepare_runtime(self.jar,self.front,self.cache)
        self.assertEqual(fallback.jar,first.jar)
        self.assertTrue(fallback.warning)
    def test_incomplete_first_build_cannot_start(self):
        self.jar.write_bytes(b'thin-or-partial')
        with self.assertRaises(RuntimeError):prepare_runtime(self.jar,self.front,self.cache)
    def test_missing_frontend_asset_is_detected(self):
        (self.front/'assets/main.js').unlink()
        with self.assertRaises(RuntimeError):prepare_runtime(self.jar,self.front,self.cache)
    def test_new_frontend_does_not_modify_previous_runtime(self):
        first=prepare_runtime(self.jar,self.front,self.cache)
        (self.front/'assets/main.js').write_text('console.log("next")',encoding='utf-8')
        second=prepare_runtime(self.jar,self.front,self.cache)
        self.assertNotEqual(first.frontend,second.frontend)
        self.assertEqual((first.frontend/'assets/main.js').read_text(),'console.log("ready")')
    def test_corrupt_frontend_cache_is_rebuilt_from_complete_source(self):
        first=prepare_runtime(self.jar,self.front,self.cache)
        mark_runtime_ready(first,self.cache)
        (first.frontend/'assets/main.js').unlink()
        repaired=prepare_runtime(self.jar,self.front,self.cache)
        self.assertNotEqual(repaired.frontend,first.frontend)
        self.assertEqual((repaired.frontend/'assets/main.js').read_text(),'console.log("ready")')

if __name__=='__main__':unittest.main()
