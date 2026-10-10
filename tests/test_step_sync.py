"""Verify that teaching and the browser share one numbered step cursor."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT
sys.path.insert(0,str(SKILL/'scripts'))
import workbench
from design_engine import normalize, REGISTRY

class StepSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'project with spaces'
        shutil.copytree(SKILL/'templates/course-example',self.root)
        (self.root/'agent-design').mkdir(exist_ok=True)
        shutil.copy2(SKILL/'templates/example-state.json',self.root/'agent-design/teaching-state.json')
        self.project=workbench.Project(self.root)
        self.server=workbench.make_server(self.project,SKILL/'assets/workbench',0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.snapshot=self.get()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()

    def get(self,path='/api/snapshot'):
        with urllib.request.urlopen(self.url+path) as r:return json.loads(r.read())

    def post(self,data):
        headers={'Content-Type':'application/json','Origin':self.url,'X-Workbench-Token':self.snapshot['token']}
        req=urllib.request.Request(self.url+'/api/progress',json.dumps(data).encode(),headers=headers)
        try:
            with urllib.request.urlopen(req) as r:return r.status,json.loads(r.read())
        except urllib.error.HTTPError as e:return e.code,json.loads(e.read())

    def cli(self,*args):
        result=subprocess.run([sys.executable,'-X','utf8',str(SKILL/'scripts/design_engine.py'),'--project',str(self.root),*args],capture_output=True,text=True,encoding='utf-8',check=True)
        return json.loads(result.stdout)

    def test_registry_restores_order_names_and_preserves_work(self):
        original=copy.deepcopy(self.snapshot['state']);old=copy.deepcopy(original)
        old['modules'].reverse();old['modules'][0]['title']='旧版交付与打包';old['learning_stage']='define'
        old['current_module']='tools';old['modules'][0]['decisions']='已有设计内容'
        new=normalize(old)
        self.assertEqual([(m['id'],m['number'],m['title']) for m in new['modules']],[(s['id'],s['number'],s['title']) for s in REGISTRY['steps']])
        self.assertEqual(new['modules'][-1]['decisions'],'已有设计内容')
        self.assertEqual(new['learning_stage'],'expand')
        self.assertEqual(new['design'],original['design'])

    def test_browser_cursor_is_read_by_teaching_cli(self):
        code,result=self.post({'module':'tools','action':'确定查询参数','expected_revision':self.snapshot['revision']})
        self.assertEqual(code,200);self.assertEqual(result['progress']['number'],5)
        self.assertEqual(result['progress']['label'],'第 05/15 步 · 工具')
        self.assertEqual(self.cli('--progress'),result['progress'])
        self.assertEqual(json.loads(self.project.state_path.read_text(encoding='utf-8'))['current_module'],'tools')

    def test_teaching_cursor_is_read_by_browser_poll(self):
        result=self.cli('--set-step','nodes','--action','编写检索处理函数','--sync','--progress')
        latest=self.get('/api/snapshot?revision='+self.snapshot['revision'])
        self.assertNotIn('unchanged',latest);self.assertEqual(result,latest['progress'])
        self.assertEqual(latest['progress']['number'],9);self.assertEqual(latest['state']['learning_stage'],'expand')

    def test_switch_never_completes_or_changes_design_code(self):
        before=self.snapshot['state'];sources={p:p.read_bytes() for p in self.root.rglob('*.py')}
        code,result=self.post({'module':'delivery','expected_revision':self.snapshot['revision']})
        self.assertEqual(code,200)
        self.assertEqual([m['status'] for m in before['modules']],[m['status'] for m in result['state']['modules']])
        self.assertEqual(before['design'],result['state']['design'])
        self.assertEqual(before.get('design_changes'),result['state'].get('design_changes'))
        self.assertEqual(sources,{p:p.read_bytes() for p in sources})

    def test_stale_cursor_does_not_overwrite_workbuddy_update(self):
        self.cli('--set-step','memory','--action','确定保留字段','--sync','--progress')
        before=self.project.state_path.read_bytes()
        self.assertEqual(self.post({'module':'goal','expected_revision':self.snapshot['revision']})[0],409)
        self.assertEqual(before,self.project.state_path.read_bytes())

    def test_invalid_cursor_and_action_do_not_write(self):
        before=self.project.state_path.read_bytes()
        for payload in ({'module':'new-step'},{'module':'tools','action':'x'*1001}):
            self.assertEqual(self.post({**payload,'expected_revision':self.snapshot['revision']})[0],400)
        self.assertEqual(before,self.project.state_path.read_bytes())

    def test_poll_and_idempotent_switch(self):
        result=self.post({'module':'edges','expected_revision':self.snapshot['revision']})[1]
        self.assertNotEqual(result['revision'],self.snapshot['revision'])
        self.assertTrue(self.get('/api/snapshot?revision='+result['revision'])['unchanged'])
        again=self.post({'module':'edges','expected_revision':result['revision']})[1]
        self.assertEqual(again['revision'],result['revision'])

    def test_step_reset_clears_old_subtask(self):
        first=self.post({'module':'tools','action':'配置查询参数','expected_revision':self.snapshot['revision']})[1]
        same=self.post({'module':'tools','expected_revision':first['revision']})[1]
        self.assertEqual(same['progress']['action'],'配置查询参数');self.assertEqual(same['revision'],first['revision'])
        next_step=self.post({'module':'knowledge','expected_revision':first['revision']})[1]
        self.assertEqual(next_step['progress']['action'],'');self.assertEqual(next_step['progress']['number'],6)

if __name__=='__main__':unittest.main(verbosity=2)
