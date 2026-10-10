"""Explain each teaching structure's real place in the saved business graph."""
import copy


def validate_bindings(bindings):
    if not isinstance(bindings, dict): raise ValueError('结构映射必须为按步骤 ID 保存的对象。')
    allowed = {'goal', 'io', 'model', 'prompt', 'tools', 'knowledge', 'memory', 'state', 'nodes', 'edges', 'routing', 'loops', 'control', 'evaluation', 'delivery'}
    for key, binding in bindings.items():
        if key not in allowed or not isinstance(binding, dict): raise ValueError('结构映射需要有效步骤 ID 与对象。')
        if binding.get('kind', 'runtime') not in ('runtime', 'configuration', 'global', 'not-used'): raise ValueError('结构映射类型须为运行、配置、整体或未采用。')
        for field in ('nodes', 'controls'):
            value = binding.get(field, [])
            if not isinstance(value, list) or any(not isinstance(x, str) for x in value): raise ValueError(f'{key}.{field} 必须为文字列表。')
        for field in ('summary', 'basis'):
            if field in binding and not isinstance(binding[field], str): raise ValueError(f'{key}.{field} 必须为文字。')
        edges = binding.get('edges', [])
        if not isinstance(edges, list) or any(not isinstance(e, dict) or not isinstance(e.get('from'), str) or not isinstance(e.get('to'), str) for e in edges): raise ValueError('结构映射连接需要 from 和 to。')
        if 'internal_graph' in binding:
            graph = binding['internal_graph']
            if not isinstance(graph, dict) or not isinstance(graph.get('nodes'), list) or not isinstance(graph.get('edges'), list): raise ValueError('内部教学图需要节点与连线列表。')
            ids = [n.get('id') if isinstance(n, dict) else None for n in graph['nodes']]
            if any(not isinstance(n, str) or not n for n in ids) or len(ids) != len(set(ids)): raise ValueError('内部教学图节点 ID 必须为唯一文字。')
            if any(not isinstance(e, dict) or e.get('from') not in ids or e.get('to') not in ids for e in graph['edges']): raise ValueError('内部教学图连接需要指向图内节点。')


def structure_views(state):
    graph = state['design']['graph']
    contracts = state['design']['contracts']
    nodes = {n['id']: n for n in graph['nodes']}
    specs = contracts.get('nodes', {})
    bindings = state['design'].get('structure_bindings', {})
    validate_bindings(bindings)
    models = [n['id'] for n in graph['nodes'] if n.get('kind') in ('模型', 'model')]
    dynamic = state['design']['system'].get('dynamic_node')
    if dynamic in nodes and dynamic not in models: models.append(dynamic)
    result = {}
    for module in state['modules']:
        key = module['id']; binding = bindings.get(key, {})
        issues = []; controls = []; selected = []; edges = []
        kind = 'runtime'; basis = '由当前节点与结构契约推导'
        if binding:
            kind = binding.get('kind', 'runtime')
            selected = list(binding.get('nodes', []))
            edges = list(binding.get('edges', []))
            controls = list(binding.get('controls', []))
            basis = binding.get('basis', '教练根据实际设计登记的结构对应关系')
        elif key in ('model', 'prompt'):
            selected = models; kind = 'configuration'
            controls = ['模型负责语言处理与动态决策' if key == 'model' else '提示词约束这些模型节点使用的任务、资料、格式和边界']
        elif key == 'tools':
            for name, spec in contracts.get('tools', {}).items():
                if spec.get('node'): selected.append(spec['node'])
                controls.append(name + '：输入 ' + ', '.join(spec.get('input', {})) + '；输出 ' + ', '.join(spec.get('output', {})) + '；失败：' + str(spec.get('failure', '待定义')))
        elif key == 'routing':
            selected = list(contracts.get('routes', {}))
            for source, routes in contracts.get('routes', {}).items():
                for route in routes:
                    edges.append({'from': source, 'to': route.get('to')})
                    condition = '兜底' if route.get('op') == 'default' else f"{route.get('field', '')} {route.get('op', '')} {route.get('value', '')}".strip()
                    controls.append(f"{source}：{condition} → {route.get('to', '')}")
        elif key == 'loops':
            selected = list(contracts.get('loop_limits', {}))
            for node, limit in contracts.get('loop_limits', {}).items():
                controls.append(f"{node}：计数 {limit.get('counter', '待定义')}，上限 {limit.get('max', '待定义')}，退出 {limit.get('exit', '待定义')}")
        elif key in ('nodes', 'edges', 'state', 'evaluation', 'delivery'):
            selected = list(nodes)
            if key == 'edges': edges = copy.deepcopy(graph['edges'])
            kind = 'global' if key in ('evaluation', 'delivery', 'state') else 'runtime'
            controls = [{'nodes': '定义每个处理站的读写字段、动作与实现', 'edges': '控制节点间的执行顺序与结束出口', 'state': '共享字段与更新规则贯穿实际读写节点', 'evaluation': '验证整个流程的输入、路径与结果；不是运行中的处理节点', 'delivery': '整理完整设计与实现材料；不是运行中的处理节点'}[key]]
        elif key == 'io':
            selected = [n for n in nodes if n in ('START', 'END') or set(specs.get(n, {}).get('reads', [])) & set(contracts.get('inputs', [])) or set(specs.get(n, {}).get('writes', [])) & set(contracts.get('outputs', []))]
            kind = 'global'; controls = ['输入：' + ', '.join(contracts.get('inputs', [])), '输出：' + ', '.join(contracts.get('outputs', []))]
        else:
            # Artifacts may carry an explicit business-node relationship. Never guess by ID.
            for artifact in module.get('artifacts', []):
                selected.extend(artifact.get('graph_nodes', []))
            kind = 'configuration'
        if module.get('status') == 'skipped' and binding and kind != 'not-used' and selected:
            issues.append('模块仍标记为不采用，但已登记实际作用节点，请复核模块状态。')
        if (module.get('status') == 'skipped' and not binding) or kind == 'not-used':
            selected = []; edges = []; kind = 'not-used'
        unknown = [node for node in selected if node not in nodes]
        if unknown: issues.append('对应节点已不存在：' + '、'.join(unknown))
        selected = list(dict.fromkeys(node for node in selected if node in nodes))
        valid_edges = []
        for edge in edges:
            found = next((e for e in graph['edges'] if e['from'] == edge.get('from') and e['to'] == edge.get('to')), None)
            if found: valid_edges.append(copy.deepcopy(found))
            else: issues.append(f"对应连接已不存在：{edge.get('from')} → {edge.get('to')}")
        if not binding.get('edges') and key != 'routing' and selected:
            valid_edges = [copy.deepcopy(e) for e in graph['edges'] if (e['from'] in selected and e['to'] in selected) or (key in ('tools', 'knowledge', 'loops') and e['from'] in selected)]
        focus = set(selected); context = set()
        for edge in graph['edges']:
            if edge['from'] in focus or edge['to'] in focus: context.update((edge['from'], edge['to']))
        context -= focus
        local = {'nodes': [copy.deepcopy(n) for n in graph['nodes'] if n['id'] in focus | context],
                 'edges': [copy.deepcopy(e) for e in graph['edges'] if e['from'] in focus or e['to'] in focus]}
        if not selected and kind != 'not-used':
            kind = 'unmapped'; issues.append('尚未登记本结构与实际运行节点的对应关系；由 WorkBuddy 补齐后显示。')
        reads = sorted({field for node in selected for field in specs.get(node, {}).get('reads', [])})
        writes = sorted({field for node in selected for field in specs.get(node, {}).get('writes', [])})
        result[key] = {'module': key, 'kind': kind, 'node_ids': selected, 'edges': valid_edges,
                       'context_ids': sorted(context), 'local_graph': local, 'reads': reads, 'writes': writes,
                       'controls': controls, 'basis': basis, 'issues': issues,
                       'summary': module.get('decision') or binding.get('summary', ''),
                       'internal_graph': copy.deepcopy(binding.get('internal_graph', module.get('graph', {'nodes': [], 'edges': []})))}
    return result
