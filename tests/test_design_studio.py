import copy
import subprocess
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SKILL=ROOT
sys.path.insert(0,str(SKILL/'scripts'))
from design_engine import normalize, derived, audit, grade, mastery_hash, fingerprint, change_record, design_change_hash
from workbench import Project, Conflict
from render_board import validate
from run_design import run

class Changes(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        shutil.copytree(SKILL/'templates/course-example',self.root,dirs_exist_ok=True)
        self.s=normalize(json.loads((SKILL/'templates/example-state.json').read_text(encoding='utf-8')))
        for m in self.s['modules']: m['presentation_status']='shown'
        self.write(self.s);self.p=Project(self.root);self.save(self.s)
    def tearDown(self): self.tmp.cleanup()
    def write(self,s): (self.root/'agent-design/teaching-state.json').write_text(json.dumps(s,ensure_ascii=False),encoding='utf-8')
    def save(self,s): return self.p.save_state({'state':s,'expected_revision':self.p.snapshot()['revision']})
    def completed(self):
        s=self.p.state();s['open_questions']=[]
        for m in s['modules']:
            m['status']='done';m['presentation_status']='shown';m['check']='实际文件、契约与本步决定一致。'
            m.pop('exercise',None);m.pop('mastery',None)
        return s
    def test_completed_requires_real_evidence(self):
        s=self.completed();self.save(s)
        report=audit(self.p.state(),self.root)
        self.assertTrue(report['passed'],report['issues'])
        s=self.p.state();s['design_status']='设计完成';self.save(s)
        bad=self.p.state();bad['agent_graph']['edges']=[];bad['design']['graph']['edges']=[]
        with self.assertRaises(ValueError): validate(bad)
        (self.root/'implementation/tools.py').unlink()
        self.assertFalse(audit(self.p.state(),self.root)['passed'])
    def test_contract_paths_and_field_sources(self):
        s=self.completed();s['design']['contracts']['nodes']['answer']['reads'].append('never_created')
        report=audit(s,self.root)
        self.assertTrue(any('never_created' in i['message'] for i in report['issues']))
        s=self.completed();s['design']['graph']['edges']=[e for e in s['design']['graph']['edges'] if e['to']!='END']
        self.assertTrue(any('出口' in i['message'] for i in audit(s,self.root)['issues']))
    def test_layout_does_not_invalidate(self):
        s=self.completed();self.save(s);s=self.p.state()
        s['agent_graph']['nodes'][0]['x']+=15
        saved=self.save(s)['state']
        self.assertEqual(saved['sync']['implementation_pending'],[])
        self.assertTrue(all('mastery' not in m for m in saved['modules']))
    def test_wording_only_reexplain(self):
        s=self.completed();self.save(s);s=self.p.state();s['agent_graph']['nodes'][0]['label']='入口的新说明'
        saved=self.save(s)['state'];self.assertEqual(saved['sync']['implementation_pending'],[])
        self.assertTrue(all('mastery' not in m for m in saved['modules']))
        self.assertEqual(next(m for m in saved['modules'] if m['id']=='nodes')['presentation_status'],'review')
    def test_canonical_docs_and_targeted_dependency(self):
        s=self.completed();self.save(s);s=self.p.state()
        next(m for m in s['modules'] if m['id']=='prompt')['decision']='回答必须引用课程目录来源。'
        saved=self.save(s)['state']
        self.assertEqual(saved['design']['component_decisions']['prompt'],'回答必须引用课程目录来源。')
        self.assertIn('回答必须引用课程目录来源。',(self.root/'agent-design/design-summary.md').read_text(encoding='utf-8'))
        status={m['id']:m['presentation_status'] for m in saved['modules']}
        self.assertEqual(status['nodes'],'review');self.assertEqual(status['memory'],'shown')
        self.assertIn('nodes',saved['sync']['implementation_pending'])
    def test_canonical_conflict_and_generated_file_protection(self):
        s=self.p.state();s['design']['component_decisions']['goal']='甲';s['modules'][0]['decision']='乙'
        with self.assertRaises(ValueError): self.save(s)
        file=next(f for f in self.p.snapshot()['files'] if f['path']=='agent-design/design-summary.md')
        with self.assertRaises(ValueError): self.p.save_file({'path':file['path'],'content':'破坏','expected_sha':file['sha']})
        (self.root/'agent-design/design-summary.md').write_text('已有手写内容',encoding='utf-8')
        with self.assertRaises(Conflict):self.save(self.p.state())
        self.assertEqual((self.root/'agent-design/design-summary.md').read_text(encoding='utf-8'),'已有手写内容')
    def test_no_quiz_gate_or_note_generation(self):
        s=self.completed();self.save(s)
        self.assertTrue(audit(self.p.state(),self.root)['passed'])
        for m in self.p.state()['modules']:
            self.assertFalse({'exercise','mastery','notes'} & m.keys())
        # Historical wrong answers do not obstruct otherwise complete actual design.
        s=self.p.state()
        for m in s['modules']:m['mastery']={'status':'retry','answer':-1,'reason':'旧记录'}
        self.save(s);self.assertTrue(audit(self.p.state(),self.root)['passed'])

    def test_genuine_graph_diff_and_layout(self):
        s=self.p.state();before=copy.deepcopy(s)
        s['design']['graph']['nodes'][0]['x']+=50
        s['agent_graph']=copy.deepcopy(s['design']['graph'])
        self.assertIsNone(change_record(s,before))
        s['design']['graph']['nodes'][0]['label']='课堂入口'
        s['design']['graph']['edges'][0]['label']='接收问题'
        event=change_record(s,before)
        self.assertIn('START',event['changed']);self.assertTrue(event['edges_changed'])
        self.assertEqual(event['before_graph'],before['design']['graph'])
        self.assertEqual(event['after_graph'],s['design']['graph'])

    def test_client_cannot_fabricate_change_history(self):
        s=self.p.state();before=copy.deepcopy(s['design_changes'])
        s['design_changes'].append({'id':'fake','summary':'伪造已新增工具'})
        saved=self.save(s)['state'];self.assertEqual(saved['design_changes'],before)
        next(m for m in saved['modules'] if m['id']=='prompt')['decision']='回答只使用已查到的课程资料。'
        result=self.save(saved)['state'];self.assertEqual(result['design_changes'][-1]['decisions'][0]['module'],'prompt')

    def test_request_queue_conflicts_and_honest_application(self):
        revision=self.p.snapshot()['revision'];before=self.p.state()['design_changes']
        result=self.p.design_request({'text':'把查询节点改名为课程检索','module':'tools','node':'search','expected_revision':revision})
        request=result['state']['design_requests'][-1]
        self.assertEqual(request['status'],'queued');self.assertEqual(result['state']['design_changes'],before)
        with self.assertRaises(Conflict):self.p.design_request({'text':'另一条需求','expected_revision':revision})
        command=[sys.executable,'-X','utf8',str(SKILL/'scripts/design_engine.py'),'--project',str(self.root),'--resolve-request',request['id'],'--basis','已改变节点名称并同步架构文件，代码实现保持原流程。']
        result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8');self.assertNotEqual(result.returncode,0);self.assertIn('尚未实际改变',result.stderr)
        s=self.p.state();s['agent_graph']['nodes'][0]['x']+=5;self.save(s)
        self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
        s=self.p.state();next(n for n in s['agent_graph']['nodes'] if n['id']=='search')['label']='课程检索'
        self.save(s);result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8');self.assertEqual(result.returncode,0,result.stderr)
        resolved=self.p.state()['design_requests'][-1];self.assertEqual(resolved['status'],'applied');self.assertIn('架构文件',resolved['response'])
        self.assertIn('search',self.p.state()['design_changes'][-1]['changed'])

    def test_new_node_needs_contract_and_real_source(self):
        s=self.completed();g=s['design']['graph'];old=next(e for e in g['edges'] if e['from']=='answer')
        g['edges'].remove(old);g['nodes'].append({'id':'review_new','label':'人工审核','kind':'人工','description':'审核输出'})
        g['edges'] += [{'from':'answer','to':'review_new'},{'from':'review_new','to':'END'}]
        s['agent_graph']=copy.deepcopy(g)
        report=audit(s,self.root);self.assertFalse(report['passed']);self.assertTrue(any('review_new' in i['message'] for i in report['issues']))
        s['design']['contracts']['nodes']['review_new']={'reads':['answer'],'writes':[],'source':'','function':'','preview_update':{}}
        report=audit(s,self.root);self.assertTrue(any('绑定' in i['message'] for i in report['issues']))

    def test_comment_and_section_changes_precise(self):
        s=self.completed();self.save(s)
        f=next(f for f in self.p.snapshot()['files'] if f['path']=='implementation/tools.py')
        saved=self.p.save_file({'path':f['path'],'content':f['content']+'\n# 课堂说明\n','expected_sha':f['sha']})['state']
        self.assertEqual(saved['sync']['implementation_pending'],[])
        self.assertEqual(next(m for m in saved['modules'] if m['id']=='memory')['presentation_status'],'shown')
    def test_actual_workflow_six_cases_and_modes(self):
        for question,target in [('Python','answer'),('','ask'),('不存在的课程','missing'),('帮我转账','outside'),(42,'invalid')]:
            result=run(self.root,'framework',question)
            self.assertEqual(result['status'],'executed',result)
            self.assertEqual(result['events'][-1]['node'],target)
            for e in result['events']:
                self.assertTrue(e['source']['line']>0);self.assertEqual(e['after'],{**e['before'],**e['update']})
        catalog=self.root/'implementation/course_catalog.json';catalog.write_text('bad-json',encoding='utf-8')
        sys.modules.pop('tools',None) # modules may otherwise refer to previous temporary fixture
        result=run(self.root,'framework','Python');self.assertEqual(result['events'][-1]['node'],'error')
        result=run(self.root,'design','Python');self.assertEqual(result['status'],'simulated')
        self.assertTrue(all(not e['source'] for e in result['events']))
        import os
        from unittest.mock import patch
        with patch.dict(os.environ,{'OPENAI_API_KEY':''}):
            result=run(self.root,'real','Python');self.assertEqual(result['status'],'failed');self.assertFalse(result['events'])
    def test_dynamic_agent_tool_message_and_bound(self):
        s=json.loads((SKILL/'templates/agent-comparison-state.json').read_text(encoding='utf-8'));self.write(s)
        sys.modules.pop('tools',None)
        result=run(self.root,'framework','Python')
        self.assertEqual(result['status'],'executed',result)
        self.assertEqual([e['node'] for e in result['events']],['model','tools','model'])
        messages=result['output']['messages'];call=messages[1]['data']['tool_calls'][0]['id'];self.assertEqual(messages[2]['data']['tool_call_id'],call)
        self.assertLessEqual(result['output']['attempts'],3)
        s['design']['contracts']['loop_limits']={}
        self.assertTrue(any(i['module']=='loops' for i in audit(s,self.root)['issues']))

    def test_workbench_child_unicode_and_invalid_input(self):
        sys.modules.pop('tools',None)
        result=self.p.run({'mode':'framework','question':'Python','expected_revision':self.p.snapshot()['revision']})
        self.assertEqual(result['run_result']['status'],'executed',result.get('run_result'))
        self.assertIn('模拟模型',result['run_result']['output']['answer'])
        result=self.p.run({'mode':'framework','question':42,'expected_revision':self.p.snapshot()['revision']})
        self.assertEqual(result['state']['trace'][-1]['node'],'invalid')

    def test_external_mirror_edit_not_silently_lost(self):
        s=self.p.state();s['modules'][0]['decision']='只服务本校学生，不代报名。';self.write(s)
        current=self.p.state();self.assertEqual(current['design']['component_decisions']['goal'],'只服务本校学生，不代报名。')
        result=self.save(current)
        self.assertIn('只服务本校学生',(self.root/'agent-design/design-summary.md').read_text(encoding='utf-8'))
        self.assertIn('io',result['state']['sync']['implementation_pending'])

if __name__=='__main__':unittest.main()
