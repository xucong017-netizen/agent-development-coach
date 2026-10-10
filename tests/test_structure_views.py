import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SKILL=ROOT
sys.path.insert(0,str(SKILL/'scripts'))
from design_engine import normalize,execution_hash,design_change_hash,change_record
from structure_views import structure_views
from workbench import Project

class StructureViewTests(unittest.TestCase):
    def setUp(self):self.s=normalize(json.loads((SKILL/'templates/example-state.json').read_text(encoding='utf-8')))

    def test_tool_local_graph_is_real_subset_with_boundaries(self):
        scope=structure_views(self.s)['tools'];self.assertEqual(scope['node_ids'],['search'])
        local=scope['local_graph'];self.assertEqual({n['id'] for n in local['nodes']},{'validate','search','error','missing','answer'})
        self.assertNotIn('START',{n['id'] for n in local['nodes']})
        for edge in local['edges']:self.assertIn(edge,self.s['agent_graph']['edges'])
        self.assertEqual({e['to'] for e in scope['edges']},{'answer','error','missing'})
        self.assertEqual(scope['reads'],['topic']);self.assertEqual(scope['writes'],['documents','error','source'])

    def test_configuration_shares_real_model_node(self):
        scopes=structure_views(self.s)
        self.assertEqual(scopes['model']['node_ids'],['answer']);self.assertEqual(scopes['prompt']['node_ids'],['answer'])
        self.assertEqual(scopes['prompt']['kind'],'configuration')
        self.assertIn('提示词',self.s['modules'][3]['title'])

    def test_unused_is_distinct_from_missing_mapping(self):
        scopes=structure_views(self.s)
        for key in ('memory','control','loops'):
            self.assertEqual(scopes[key]['kind'],'not-used');self.assertFalse(scopes[key]['node_ids']);self.assertFalse(scopes[key]['local_graph']['nodes'])
        self.s['design']['structure_bindings'].pop('memory')
        next(m for m in self.s['modules'] if m['id']=='memory')['status']='done'
        missing=structure_views(self.s)['memory'];self.assertEqual(missing['kind'],'unmapped');self.assertTrue(missing['issues'])

    def test_routes_highlight_real_control_edges(self):
        scope=structure_views(self.s)['routing'];self.assertEqual(set(scope['node_ids']),{'validate','search'})
        self.assertEqual(len(scope['edges']),7);self.assertTrue(any('兜底' in x for x in scope['controls']))
        self.assertNotIn({'from':'answer','to':'END','label':'完成'},scope['edges'])

    def test_unknown_node_never_falls_back_to_first_node(self):
        self.s['design']['structure_bindings']['knowledge']['nodes']=['removed_query']
        scope=structure_views(self.s)['knowledge'];self.assertFalse(scope['node_ids']);self.assertEqual(scope['kind'],'unmapped')
        self.assertTrue(any('removed_query' in x for x in scope['issues']))

    def test_contract_fallback_works_for_arbitrary_node_ids(self):
        self.s['design']['structure_bindings'].pop('tools')
        for node in self.s['design']['graph']['nodes']:
            if node['id']=='search':node['id']='catalog_query_42'
        for edge in self.s['design']['graph']['edges']:
            for key in ('from','to'):
                if edge[key]=='search':edge[key]='catalog_query_42'
        self.s['design']['contracts']['tools']['search_courses']['node']='catalog_query_42'
        self.s['design']['contracts']['nodes']['catalog_query_42']=self.s['design']['contracts']['nodes'].pop('search')
        scope=structure_views(self.s)['tools'];self.assertEqual(scope['node_ids'],['catalog_query_42'])
        self.assertEqual(scope['reads'],['topic'])

    def test_explanatory_metadata_preserves_execution_evidence(self):
        before=copy.deepcopy(self.s);self.s['design']['structure_bindings']['tools']['basis']='新的准确展示说明'
        self.assertEqual(execution_hash(before['design']),execution_hash(self.s['design']))
        self.assertEqual(design_change_hash(before['design']),design_change_hash(self.s['design']))
        self.assertIsNone(change_record(self.s,before))
        self.s['design']['component_decisions']['tools']+=' 修改业务参数'
        self.assertNotEqual(execution_hash(before['design']),execution_hash(self.s['design']))

    def test_saved_mapping_and_new_graph_refresh_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);shutil.copytree(SKILL/'templates/course-example',root,dirs_exist_ok=True)
            state_path=root/'agent-design/teaching-state.json';state_path.write_text(json.dumps(self.s,ensure_ascii=False),encoding='utf-8')
            project=Project(root);before=project.snapshot()
            s=project.state();s['design']['graph']['nodes'].append({'id':'review_result','label':'审核查询结果','kind':'人工'})
            s['design']['graph']['edges'].append({'from':'search','to':'review_result','label':'待审核'})
            s['design']['structure_bindings']['control']={'kind':'runtime','nodes':['review_result'],'controls':['确认后才允许交付']}
            state_path.write_text(json.dumps(s,ensure_ascii=False),encoding='utf-8')
            latest=project.snapshot();self.assertNotEqual(before['revision'],latest['revision'])
            self.assertEqual(latest['structure_views']['control']['node_ids'],['review_result'])
            self.assertIn('review_result',{n['id'] for n in latest['structure_views']['tools']['local_graph']['nodes']})

    def test_invalid_mapping_is_rejected_before_write(self):
        for change in ({'nodes':'search'},{'edges':[{'from':'search'}]},{'internal_graph':{'nodes':[{'id':'x'}],'edges':[{'from':'x','to':'absent'}]}}):
            bad=copy.deepcopy(self.s);bad['design']['structure_bindings']['tools'].update(change)
            with self.assertRaises(ValueError):normalize(bad)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);shutil.copytree(SKILL/'templates/course-example',root,dirs_exist_ok=True)
            state_path=root/'agent-design/teaching-state.json';state_path.write_text(json.dumps(self.s),encoding='utf-8')
            project=Project(root);before=state_path.read_bytes();bad=project.state()
            bad['design']['structure_bindings']['tools']['nodes']='invalid'
            with self.assertRaises(ValueError):project.save_state({'state':bad,'expected_revision':project.snapshot()['revision']})
            self.assertEqual(before,state_path.read_bytes())

    def test_global_structures_do_not_invent_runtime_nodes(self):
        scopes=structure_views(self.s)
        for key in ('state','evaluation','delivery'):
            self.assertEqual(scopes[key]['kind'],'global')
            self.assertEqual(set(scopes[key]['node_ids']),{n['id'] for n in self.s['agent_graph']['nodes']})
        self.assertEqual(set(scopes),{m['id'] for m in self.s['modules']})

if __name__=='__main__':unittest.main(verbosity=2)
