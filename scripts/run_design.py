"""Execute the saved graph and registered project node functions; emit inspectable JSON."""
import argparse
import copy
import importlib.util
import inspect
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import TypedDict
from design_engine import normalize, execution_hash, safe_file

def run(root, mode, question):
    run_id = str(uuid.uuid4()); events = []
    data = {'run': run_id, 'mode': mode, 'status': 'failed', 'events': events,
            'evidence': '预期流程，未执行框架或模型' if mode == 'design' else '实际 LangGraph；模拟模型' if mode == 'framework' else '实际 LangGraph；真实模型调用', 'error': ''}
    try:
        state = normalize(json.loads((root / 'agent-design/teaching-state.json').read_text(encoding='utf-8-sig')))
        design = state['design']; contracts = design['contracts']; graph = design['graph']
        data['design_hash'] = execution_hash(design)
        data['source_hashes'] = {}
        for folder in ('implementation',):
            for path in (root / folder).rglob('*'):
                if path.is_file() and path.suffix in ('.py', '.json') and path.resolve().is_relative_to(root.resolve()) and not path.is_symlink():
                    data['source_hashes'][path.relative_to(root).as_posix()] = __import__('hashlib').sha256(path.read_bytes()).hexdigest()
        data['executed_sources'] = []
        fields = contracts['state_fields']; node_specs = contracts['nodes']
        if not {'START', 'END'} <= {n['id'] for n in graph['nodes']}: raise ValueError('请先定义 START 和 END。')
        if mode == 'real' and not os.environ.get('OPENAI_API_KEY'): raise ValueError('真实模型未配置：在运行时环境设置 OPENAI_API_KEY；界面不会保存密钥。')
        initial = {k: copy.deepcopy(v['default']) for k, v in fields.items() if isinstance(v, dict) and 'default' in v}
        initial.update({'question': question})
        outgoing = {}
        for e in graph['edges']: outgoing.setdefault(e['from'], []).append(e['to'])
        loaded = {}; count = {}; current = copy.deepcopy(initial)

        def route(name, values):
            choices = outgoing.get(name, [])
            guard = contracts.get('loop_limits', {}).get(name)
            if guard and values.get(guard['counter'], 0) >= guard['max']: return guard['exit']
            if len(choices) == 1: return choices[0]
            rules = contracts.get('routes', {}).get(name, [])
            fallback = None
            for rule in rules:
                op = rule.get('op'); value = values.get(rule.get('field'))
                if op == 'default': fallback = rule['to']; continue
                if (op == 'empty' and not value) or (op == 'nonempty' and bool(value)) or (op == 'eq' and value == rule.get('value')):
                    if rule['to'] not in choices: raise ValueError('条件规则指向没有连线的节点。')
                    return rule['to']
            if fallback not in choices: raise ValueError(f'{name} 的路由没有有效兜底。')
            return fallback

        def emit(name, before, update, after, source, duration, error=''):
            # Public values only. Node implementations must not put secrets/private reasoning in state.
            events.append({'run': run_id, 'step': len(events) + 1, 'node': name, 'mode': mode,
                'input': before, 'before': before, 'update': update, 'after': after,
                'output': after.get('answer', ''), 'source': source, 'duration_ms': round(duration * 1000, 2),
                'error': error, 'basis': '设计模拟：预设更新' if mode == 'design' else '实际节点函数执行'})

        if mode == 'design':
            name = route('START', current)
            for _ in range(40):
                if name == 'END': break
                spec = node_specs.get(name, {})
                before = copy.deepcopy(current); update = copy.deepcopy(spec.get('preview_update', {}))
                current.update(update); emit(name, before, update, copy.deepcopy(current), {}, 0)
                name = route(name, current)
            else: raise ValueError('设计模拟超过 40 步，检查循环。')
            data['status'] = 'simulated'; data['output'] = current
            return data

        try:
            from langgraph.graph import StateGraph, START, END
        except ImportError: raise ValueError('此 Python 环境缺少 langgraph。代码实践时由 Skill 安装 requirements-runtime.txt；设计模式不需要。')
        # Actual saved state schema; dict defaults are deliberate and shown in the contract editor.
        Schema = TypedDict('AgentState', {key: object for key in fields}, total=False)
        builder = StateGraph(Schema)
        mapping = {'START': START, 'END': END}
        for n in graph['nodes']:
            name = n['id']
            if name in mapping: continue
            spec = node_specs.get(name, {}); path = safe_file(root, spec.get('source', ''))
            if not path or not path.is_file() or path.suffix != '.py': raise ValueError(f'{name} 没有有效 Python 源文件。')
            data['source_hashes'][spec['source']] = __import__('hashlib').sha256(path.read_bytes()).hexdigest()
            if str(path) not in loaded:
                sys.path.insert(0, str(path.parent))
                module_spec = importlib.util.spec_from_file_location('project_' + str(len(loaded)), path)
                module = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(module)
                loaded[str(path)] = module
            function = getattr(loaded[str(path)], spec.get('function', ''), None)
            if not callable(function): raise ValueError(f'{name} 的绑定函数不存在。')
            source = {'path': spec['source'], 'function': function.__name__, 'line': inspect.getsourcelines(function)[1]}
            def wrapped(values, name=name, function=function, source=source, spec=spec):
                before = copy.deepcopy(dict(values)); started = time.perf_counter()
                if source['path'] not in data['executed_sources']: data['executed_sources'].append(source['path'])
                count[name] = count.get(name, 0) + 1
                if count[name] > 40: raise ValueError('单节点次数超过限制。')
                try:
                    missing = [k for k in spec.get('reads', []) if k not in values]
                    if missing: raise ValueError('输入字段缺失：' + ','.join(missing))
                    update = function(copy.deepcopy(dict(values)), {'mode': mode, 'project': str(root)})
                    if not isinstance(update, dict) or set(update) - set(spec.get('writes', [])):
                        raise ValueError('节点返回了契约之外的字段。')
                    guard = contracts.get('loop_limits', {}).get(name)
                    if guard and (not isinstance(update.get(guard['counter']), int) or update[guard['counter']] <= values.get(guard['counter'], 0)):
                        raise ValueError('循环节点没有实际增加计数，停止运行。')
                    after = {**before, **update}
                    emit(name, before, update, after, source, time.perf_counter() - started)
                    return update
                except Exception as e:
                    emit(name, before, {}, before, source, time.perf_counter() - started, str(e)); raise
            builder.add_node(name, wrapped)
        for name, choices in outgoing.items():
            if len(choices) == 1: builder.add_edge(mapping.get(name, name), mapping.get(choices[0], choices[0]))
            else:
                builder.add_conditional_edges(mapping.get(name, name), lambda values, name=name: route(name, values),
                                              {to: mapping.get(to, to) for to in choices})
        compiled = builder.compile()
        result = compiled.invoke(initial, {'recursion_limit': 40})
        data['status'] = 'executed'; data['output'] = result
        # Running proves execution, never automatically proves business correctness or understanding.
    except Exception as error:
        data['error'] = str(error)
    return data

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--mode', choices=['design', 'framework', 'real'], required=True)
    parser.add_argument('--question', default='Python')
    parser.add_argument('--input-json', help='JSON question value, preserving invalid-type test inputs')
    args = parser.parse_args()
    question = json.loads(args.input_json) if args.input_json is not None else args.question
    print(json.dumps(run(args.project.resolve(), args.mode, question), ensure_ascii=False, default=str))

if __name__ == '__main__': main()
