#!/usr/bin/env python3
"""Render a teaching-state JSON file to a self-contained offline HTML board."""
import argparse
import html
import json
import math
import re
import sys
from pathlib import Path

# Support loading this standalone renderer by file path as well as CLI execution.
sys.path.insert(0, str(Path(__file__).resolve().parent))

STATUSES = {'pending': '待填写', 'active': '进行中', 'done': '已完成',
            'skipped': '本次不采用', 'review': '需复核'}
ID = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')
PRESENTATIONS = {'pending': '成果待展示', 'shown': '成果已展示', 'review': '成果需重讲'}


def esc(value):
    return html.escape(str(value), quote=True)


def validate_graph(graph):
    if not isinstance(graph, dict):
        raise ValueError('graph must be an object')
    nodes, edges = graph.get('nodes', []), graph.get('edges', [])
    if not isinstance(nodes, list) or not isinstance(edges, list) or len(nodes) > 60:
        raise ValueError('graph needs node/edge lists, with at most 60 nodes')
    ids = set()
    for n in nodes:
        if not isinstance(n, dict) or not ID.fullmatch(str(n.get('id', ''))):
            raise ValueError('Invalid node ID')
        if n['id'] in ids:
            raise ValueError('Duplicate node ID: ' + n['id'])
        ids.add(n['id'])
        for key in ('x', 'y'):
            if key in n and (not isinstance(n[key], (int, float)) or
                             not math.isfinite(n[key]) or not 0 <= n[key] <= 10000):
                raise ValueError('Coordinates must be finite, nonnegative, <= 10000')
    for e in edges:
        if not isinstance(e, dict) or e.get('from') not in ids or e.get('to') not in ids:
            raise ValueError('Edge points to a missing node')
    return ids


def validate(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('schema_version must be 1')
    modules = data.get('modules')
    if not isinstance(modules, list) or len(modules) != 15:
        raise ValueError('Keep all 15 teaching modules')
    ids = set()
    for m in modules:
        if not isinstance(m, dict):
            raise ValueError('Each teaching module must be an object')
        if not ID.fullmatch(str(m.get('id', ''))) or m['id'] in ids:
            raise ValueError('Invalid or duplicate module ID')
        ids.add(m['id'])
        if m.get('status') not in STATUSES:
            raise ValueError('Unknown module status')
        validate_graph(m.get('graph', {}))
        if m.get('presentation_status', 'pending') not in PRESENTATIONS:
            raise ValueError('Unknown presentation status')
        artifacts = m.get('artifacts', [])
        if not isinstance(artifacts, list):
            raise ValueError('artifacts must be a list')
        for artifact in artifacts:
            if not isinstance(artifact, dict) or not isinstance(artifact.get('content', ''), str):
                raise ValueError('Artifact needs an object with textual content')
            if not isinstance(artifact.get('explanations', []), list):
                raise ValueError('Artifact explanations must be a list')
            if any(not isinstance(e, dict) for e in artifact.get('explanations', [])):
                raise ValueError('Each block explanation must be an object')
            if not isinstance(artifact.get('verification', {}), dict):
                raise ValueError('Artifact verification must be an object')
    if data.get('current_module') not in ids:
        raise ValueError('current_module is not a module ID')
    expected = {'goal','io','model','prompt','tools','knowledge','memory','state','nodes','edges','routing','loops','control','evaluation','delivery'}
    if ids != expected: raise ValueError('Keep the original 15 component IDs')
    agent_ids = validate_graph(data.get('agent_graph', {}))
    for t in data.get('trace', []):
        if not isinstance(t, dict) or t.get('node') not in agent_ids:
            raise ValueError('Trace refers to a missing agent node')
    if not isinstance(data.get('open_questions', []), list):
        raise ValueError('open_questions must be a list')
    if not isinstance(data.get('file_catalog', []), list) or any(
            not isinstance(f, dict) for f in data.get('file_catalog', [])):
        raise ValueError('file_catalog must contain file objects')
    if 'design' in data:
        design = data['design']
        if not isinstance(design, dict) or not isinstance(design.get('component_decisions'), dict) or not isinstance(design.get('system'), dict):
            raise ValueError('design needs component_decisions and system objects')
        validate_graph(design.get('graph', {}))
        c = design.get('contracts', {})
        if not isinstance(c, dict): raise ValueError('contracts must be an object')
        for key in ('inputs', 'outputs', 'tests'):
            if not isinstance(c.get(key, []), list): raise ValueError(key + ' must be a list')
        for key in ('state_fields', 'nodes', 'tools', 'routes', 'loop_limits'):
            if not isinstance(c.get(key, {}), dict): raise ValueError(key + ' must be an object')
        if any(not isinstance(v, dict) for k in ('nodes', 'tools', 'loop_limits') for v in c.get(k, {}).values()):
            raise ValueError('Node/tool/loop contracts need object values')
        if any(not isinstance(v, list) or any(not isinstance(r, dict) for r in v) for v in c.get('routes', {}).values()):
            raise ValueError('Route contracts need lists of rule objects')
        if any(not isinstance(t, dict) for t in c.get('tests', [])): raise ValueError('tests need case objects')
        if any(not isinstance(v, dict) or v.get('type') not in ('string','integer','number','boolean','list','dict','any') for v in c.get('state_fields', {}).values()):
            raise ValueError('State fields need a supported type: string/integer/number/boolean/list/dict/any')
        if any(not isinstance(v, str) for v in c.get('inputs', []) + c.get('outputs', [])):
            raise ValueError('input/output field names must be strings')
        for spec in c.get('nodes', {}).values():
            if any(k in spec and not isinstance(spec[k], str) for k in ('source', 'function')): raise ValueError('Node source/function must be strings')
            if any(not isinstance(spec.get(k, []), list) or any(not isinstance(f, str) for f in spec.get(k, [])) for k in ('reads', 'writes')):
                raise ValueError('Node reads/writes need field-name lists')
        for rules in c.get('routes', {}).values():
            for rule in rules:
                if any(k in rule and not isinstance(rule[k], str) for k in ('field','op','to')): raise ValueError('Route field/op/to must be strings')
        for guard in c.get('loop_limits', {}).values():
            if any(k in guard and not isinstance(guard[k], str) for k in ('counter','exit')): raise ValueError('Loop counter/exit must be strings')
    if data.get('design_status') == '设计完成':
        from design_engine import audit
        result = audit(data)
        if not result['passed']: raise ValueError('设计完成验收未通过：' + result['issues'][0]['message'])


def artifacts_html(module):
    artifacts = module.get('artifacts', [])
    if not artifacts:
        return '<div class="empty">本步尚未记录实际成果。请在对话中读回文件，展示具体内容、用途和检查结果。</div>'
    output = ['<h3>本步实际文件与内容</h3>']
    labels = [('why', '为什么需要'), ('input', '接收什么'), ('action', '做什么'),
              ('output', '输出什么'), ('consequence', '改错会怎样'), ('graph_node', '对应结构')]
    for artifact in artifacts:
        output.append(f'<section class="artifact"><h3>{esc(artifact.get("path", "未指定文件"))}</h3>'
                      f'<p>{esc(artifact.get("purpose", ""))}</p>'
                      f'<p class="caption">{esc(artifact.get("kind", ""))} · '
                      f'{esc(artifact.get("change", ""))} · {esc(artifact.get("content_scope", ""))}</p>'
                      f'<pre><code>{esc(artifact.get("content", ""))}</code></pre>')
        for block in artifact.get('explanations', []):
            output.append(f'<div class="block-explanation"><h3>{esc(block.get("block", "代码块"))}</h3><dl>')
            for key, label in labels:
                output.append(f'<dt>{label}</dt><dd>{esc(block.get(key, "尚未解释"))}</dd>')
            output.append('</dl></div>')
        verification = artifact.get('verification', {})
        output.append(f'<h3>检查：{esc(verification.get("status", "未执行"))}</h3>'
                      f'<p class="caption">命令：{esc(verification.get("command", "不适用"))}</p>'
                      f'<p>预期：{esc(verification.get("expected", "尚未填写"))}</p>'
                      f'<pre class="actual">{esc(verification.get("actual") or "没有实际执行结果；不能将预期当成真实输出。")}</pre></section>')
    return ''.join(output)


def file_catalog_html(data):
    files = data.get('file_catalog', [])
    if not files:
        return '<p class="subtle">尚未登记项目文件。已有项目应先核对实际目录，再补充文件用途；不从进度状态推断文件已存在。</p>'
    rows = ''.join('<tr>' + ''.join(f'<td>{esc(f.get(k, ""))}</td>' for k in
                                  ('path', 'purpose', 'status', 'caller')) + '</tr>' for f in files)
    return '<div class="table-scroll"><table><thead><tr><th>文件</th><th>用途</th><th>状态</th><th>谁调用它</th></tr></thead><tbody>' + rows + '</tbody></table></div>'


def svg(graph, prefix):
    nodes = graph.get('nodes', [])
    if not nodes:
        return '<div class="empty">运行总图将在节点与连线设计后形成。现在先完成当前结构。</div>'
    coords = {n['id']: (n.get('x', 25 + (i % 3) * 270), n.get('y', 25 + (i // 3) * 140))
              for i, n in enumerate(nodes)}
    width = max(x for x, _ in coords.values()) + 245
    height = max(y for _, y in coords.values()) + 125
    out = [f'<svg role="img" aria-label="{esc(prefix)}结构图" viewBox="0 0 {width} {height}" '
           f'style="width:{width}px;max-width:none;height:{height}px">',
           f'<defs><marker id="arrow-{prefix}" markerWidth="8" markerHeight="8" '
           'refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#6c819b"/></marker></defs>']
    for e in graph.get('edges', []):
        ax, ay = coords[e['from']]
        bx, by = coords[e['to']]
        if e['from'] == e['to']:
            sx, sy, ex, ey = ax + 110, ay, ax + 190, ay
            d = f'M {sx} {sy} C {sx} {sy-38} {ex} {ey-38} {ex} {ey}'
            lx, ly = ax + 140, ay - 22
        elif by > ay:
            sx, sy, ex, ey = ax + 110, ay + 78, bx + 110, by
            mid = (sy + ey) / 2
            d = f'M {sx} {sy} C {sx} {mid} {ex} {mid} {ex} {ey}'
            lx, ly = (sx + ex) / 2, mid - 5
        elif by < ay:
            sx, sy, ex, ey = ax, ay + 39, bx, by + 39
            left = max(5, min(ax, bx) - 20)
            d = f'M {sx} {sy} C {left} {sy} {left} {ey} {ex} {ey}'
            lx, ly = left, (sy + ey) / 2
        else:
            sx, sy, ex, ey = (ax + 220, ay + 39, bx, by + 39) if bx > ax else (ax, ay + 39, bx + 220, by + 39)
            d = f'M {sx} {sy} L {ex} {ey}'
            lx, ly = (sx + ex) / 2, sy - 8
        out.append(f'<path d="{d}" fill="none" stroke="#6c819b" stroke-width="1.8" '
                   f'marker-end="url(#arrow-{prefix})"/>')
        label = str(e.get('label', ''))
        out.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" class="edge-label">{esc(label)}</text>')
    for n in nodes:
        x, y = coords[n['id']]
        label = str(n.get('label', n['id']))
        lines = [label[i:i+13] for i in range(0, len(label), 13)][:3] or ['']
        kind = str(n.get('kind', '结构'))
        out.append(f'<g class="node" data-node="{esc(n["id"])}"><title>{esc(label)}</title>'
                   f'<rect x="{x}" y="{y}" width="220" height="78" rx="14"/>'
                   f'<text x="{x+14}" y="{y+18}" class="kind">{esc(kind)}</text>')
        for i, line in enumerate(lines):
            out.append(f'<text x="{x+110}" y="{y+37+i*16}" text-anchor="middle" class="node-label">{esc(line)}</text>')
        out.append('</g>')
    out.append('</svg>')
    return ''.join(out)


def render(data):
    from design_engine import normalize
    data = normalize(data)
    validate(data)
    modules = data['modules']
    finished = sum(m['status'] in ('done', 'skipped') for m in modules)
    shown = sum(m.get('presentation_status') == 'shown' for m in modules)
    current = next(m for m in modules if m['id'] == data['current_module'])
    links, cards = [], []
    for i, m in enumerate(modules, 1):
        status = m['status']
        links.append(f'<a class="nav-item {status}" href="#module-{esc(m["id"])}">'
                     f'<span class="num">{i:02}</span><span>{esc(m["title"])}</span>'
                     f'<small>{STATUSES[status]} · {PRESENTATIONS[m.get("presentation_status", "pending")]}</small></a>')
        is_current = m['id'] == data['current_module']
        cards.append(f'<details class="module" id="module-{esc(m["id"])}" {"open" if is_current else ""}>'
                     f'<summary><span class="num">{i:02}</span><strong>{esc(m["title"])}</strong>'
                     f'<span class="badge {status}">{STATUSES[status]}</span></summary>'
                     f'<div class="module-body"><p class="purpose">{esc(m.get("purpose", ""))}</p>'
                     f'<p class="caption">{esc(m.get("graph_kind", "教学示意"))} · 局部结构图</p>'
                     f'<div class="graph">{svg(m.get("graph", {}), m["id"])}</div>'
                     '<div class="two-col">'
                     f'<section><h3>由什么构成</h3><p>{esc(m.get("parts", ""))}</p></section>'
                     f'<section><h3>一起填写</h3><p>{esc(m.get("question", ""))}</p></section></div>'
                     f'<div class="decision"><h3>当前决定</h3><p>{esc(m.get("decision") or "等待学员填写，示意图不是已确认设计。")}</p>'
                     f'<small>来源：{esc(m.get("origin") or "尚未选择")}</small></div>'
                     f'<p class="caption">{PRESENTATIONS[m.get("presentation_status", "pending")]}</p>'
                     f'{artifacts_html(m)}'
                     f'<p><b>业务验证依据：</b>{esc(m.get("check") or m.get("acceptance", "尚未检查"))}</p>'
                     '</div></details>')
    traces = data.get('trace', [])
    # JSON cannot close the script tag, even if learner text contains HTML.
    encoded = json.dumps(traces, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    questions = ''.join(f'<li>{esc(q)}</li>' for q in data.get('open_questions', [])) or '<li>当前无已记录的未决项；完成前仍需逐项检查。</li>'
    imp = data.get('implementation', {})
    page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ · 智能体开发教练</title><style>
:root{--ink:#18334e;--teal:#087f78;--muted:#63798d;--line:#dbe5ed;--bg:#f3f6fa}*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--bg);font:15px/1.65 "Microsoft YaHei","PingFang SC",sans-serif}header{padding:32px 5vw;background:#17324d;color:#fff}.eyebrow{font-size:12px;letter-spacing:2px;color:#a7dcd4}h1{font-size:30px;line-height:1.3;margin:8px 0}header p{color:#d5e3ef;max-width:900px}header .meta{display:flex;gap:10px;flex-wrap:wrap}.pill{border:1px solid #56758d;border-radius:30px;padding:4px 13px;font-size:12px}.layout{max-width:1600px;display:grid;grid-template-columns:290px minmax(0,1fr);gap:25px;margin:25px auto;padding:0 3vw}aside{position:sticky;top:20px;align-self:start;background:white;border:1px solid var(--line);border-radius:18px;padding:20px;max-height:calc(100vh - 40px);overflow:auto}h2{font-size:20px;margin:0 0 12px}h3{font-size:14px;margin:0 0 5px}p{margin:8px 0}.subtle,.caption{color:var(--muted);font-size:12px}.progress{height:7px;border-radius:10px;background:#e5edf4;margin:12px 0 18px;overflow:hidden}.progress div{height:100%;background:var(--teal)}.nav-item{display:grid;grid-template-columns:26px 1fr;gap:3px 8px;text-decoration:none;color:var(--ink);padding:8px 3px;border-top:1px solid #eef3f7}.nav-item small{grid-column:2;color:var(--muted);font-size:11px}.num{font-variant-numeric:tabular-nums;color:var(--teal);font-size:13px;font-weight:700}.nav-item.active{background:#edf9f6;border-radius:8px}.panel{background:#fff;border:1px solid var(--line);border-radius:18px;padding:24px;margin-bottom:18px}.panel-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.badge{font-size:11px;border-radius:30px;padding:3px 10px;background:#edf2f7;color:#596f84;white-space:nowrap}.badge.done{background:#e2f5ef;color:#08765d}.badge.active{background:#e0efff;color:#235c95}.badge.skipped{background:#f3eada;color:#876530}.badge.review{background:#ffeded;color:#a64242}.module{background:#fff;border:1px solid var(--line);border-radius:14px;margin-bottom:12px;scroll-margin-top:20px}.module summary{display:flex;align-items:center;gap:13px;cursor:pointer;padding:16px 20px;list-style:none}.module summary::after{content:'展开 +';font-size:11px;color:var(--muted);margin-left:auto}.module[open] summary::after{content:'收起 −'}.module-body{padding:0 20px 20px}.purpose{font-size:16px}.graph{overflow:auto;border:1px solid #edf1f5;border-radius:12px;background:#fbfdff;padding:14px;margin:12px 0}.node rect{fill:white;stroke:#c7d8e5;stroke-width:1.5}.node.current rect{fill:#e2f7f1;stroke:#087f78;stroke-width:3}.node-label{font-size:14px;fill:#18334e;font-weight:600}.kind{font-size:9px;fill:#668499}.edge-label{font-size:10px;fill:#526e86;paint-order:stroke;stroke:#fbfdff;stroke-width:4px}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:15px 0}.decision{background:#eff7f7;border-left:3px solid var(--teal);padding:14px;border-radius:0 8px 8px 0}.empty{padding:25px;color:var(--muted)}button{background:var(--teal);color:white;border:0;border-radius:8px;padding:9px 15px;cursor:pointer;font:inherit;font-size:13px}button:disabled{opacity:.4;cursor:default}.trace-fields{display:grid;grid-template-columns:1fr 1fr;gap:12px}.trace-fields section{padding:12px;border-radius:10px;background:#f4f7fb;overflow-wrap:anywhere}.trace-fields p{white-space:pre-wrap}.trace-controls{display:flex;align-items:center;gap:10px;margin:15px 0}.trace-controls small{margin-left:auto;color:var(--muted)}footer{color:var(--muted);font-size:12px;padding:0 5vw 25px}.focus{border-left:4px solid var(--teal)}@media(max-width:900px){.layout{grid-template-columns:1fr}aside{position:static;max-height:none}.nav-list{display:grid;grid-template-columns:1fr 1fr;gap:0 10px}h1{font-size:25px}.two-col,.trace-fields{grid-template-columns:1fr}}@media print{aside,button{display:none}.layout{display:block}.panel,.module{break-inside:avoid}header{color:#18334e;background:white}header p{color:#18334e}.graph svg{max-width:100%!important;height:auto!important}.layout{padding:0}}
.layout>*{min-width:0}.nav-item{grid-template-columns:26px minmax(0,1fr)}.module summary strong{min-width:0;flex:1}.trace-controls{flex-wrap:wrap}@media(max-width:550px){.nav-list{grid-template-columns:1fr}.panel{padding:16px}.module summary{padding:14px;gap:8px}.module summary::after{content:'+'}.module[open] summary::after{content:'−'}}
.artifact{border:1px solid var(--line);border-radius:12px;padding:16px;margin:14px 0;overflow-wrap:anywhere}.artifact h3{overflow-wrap:anywhere}pre{background:#142c42;color:#e5f2ff;border-radius:10px;padding:16px;overflow:auto;max-width:100%;font:13px/1.7 Consolas,monospace;tab-size:4}pre.actual{background:#f0f5fa;color:var(--ink)}.block-explanation{background:#f6f9fc;padding:14px;margin:12px 0;border-radius:10px}dl{display:grid;grid-template-columns:90px minmax(0,1fr);gap:5px 12px;margin:8px 0}dt{font-weight:600}dd{margin:0}.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:10px;overflow-wrap:anywhere}th{white-space:nowrap}
</style></head><body><header><div class="eyebrow">AGENT DEVELOPMENT COACH · 零基础教学向导</div><h1>__TITLE__</h1><p>一次理解一个结构，用自然语言填写设计，再沿着图解释智能体如何工作。</p><div class="meta"><span class="pill">__MODE__</span><span class="pill">__DELIVERY__</span><span class="pill">设计：__DESIGN__</span><span class="pill">代码：__IMPL__</span></div></header>
<div class="layout"><aside><h2>学习路线</h2><div class="subtle">__FINISHED__ / 15 个结构已有决定</div><div class="progress"><div style="width:__PERCENT__%"></div></div><nav class="nav-list">__NAV__</nav></aside><main>
<section class="panel focus"><div class="panel-head"><h2>当前：__CURRENT__</h2><span class="badge">__CURRENT_STATUS__</span></div><p>__CURRENT_QUESTION__</p><p class="caption">__SHOWN__ / 15 个模块成果已展示。写完文件与讲解完内容分别记录；在 WorkBuddy 对话中填写、补讲或继续。</p></section>
<section class="panel"><h2>项目文件地图</h2><p class="caption">文件用途与调用关系。教学示例文件来自附带模板，不代表已在学员项目中创建。</p>__FILE_CATALOG__</section>
<section class="panel"><div class="panel-head"><h2>智能体运行总图</h2><span class="badge">__TRACE_KIND__</span></div><p class="caption">这是业务运行结构。左侧是学习路线，两者分别记录。</p><div class="graph" id="agent-graph">__AGENT_GRAPH__</div></section>
<section class="panel"><div class="panel-head"><h2>逐步演练</h2><span class="badge">保存的可见轨迹</span></div><p class="caption">回放只展示已记录数据，不调用模型或工具；高亮表示当前回放节点。</p><div class="trace-controls"><button id="prev" type="button">上一步</button><button id="next" type="button">下一步</button><small id="position"></small></div><p id="trace-label"></p><div class="trace-fields"><section><h3>输入摘要</h3><p id="trace-input"></p></section><section><h3>状态更新</h3><p id="trace-update"></p></section><section><h3>可见输出</h3><p id="trace-output"></p></section><section><h3>判断依据</h3><p id="trace-basis"></p></section></div></section>
<h2>逐结构设计卡</h2>__CARDS__<section class="panel"><h2>未决项与实施状态</h2><ul>__QUESTIONS__</ul><p>__VERIFICATION__</p></section></main></div><footer>离线教学看板 · 15 个结构 · 无外部网络依赖 · 图示与模拟不代表代码已运行</footer>
<script id="trace-data" type="application/json">__TRACE_JSON__</script><script>
const traces=JSON.parse(document.getElementById('trace-data').textContent);let index=0;
function show(){const t=traces[index];document.getElementById('prev').disabled=!t||index===0;document.getElementById('next').disabled=!t||index===traces.length-1;document.getElementById('position').textContent=t?`${index+1} / ${traces.length}`:'尚未演练';document.getElementById('trace-label').textContent=t?`${t.run||'当前轨迹'} · 第 ${t.step} 步 · ${t.node}`:'完成节点设计后，先走一个正常例子，再走一个异常例子。';for(const k of ['input','update','output','basis']){const v=t?t[k]:'';document.getElementById('trace-'+k).textContent=typeof v==='object'?JSON.stringify(v,null,2):String(v??'');}document.querySelectorAll('#agent-graph .node').forEach(n=>n.classList.toggle('current',!!t&&n.dataset.node===t.node));}
document.getElementById('prev').addEventListener('click',()=>{index=Math.max(0,index-1);show()});document.getElementById('next').addEventListener('click',()=>{index=Math.min(traces.length-1,index+1);show()});document.querySelectorAll('.nav-item').forEach(a=>a.addEventListener('click',()=>{document.getElementById(a.getAttribute('href').slice(1)).open=true;}));show();
</script></body></html>'''
    replacements = {
        'TITLE': esc(data.get('title', '我的智能体')), 'MODE': esc(data.get('mode', '学员共创')),
        'DELIVERY': esc(data.get('delivery', '设计与代码')), 'DESIGN': esc(data.get('design_status', '进行中')),
        'IMPL': esc(imp.get('status', '未开始')), 'FINISHED': str(finished),
        'PERCENT': str(round(finished / 15 * 100)), 'NAV': ''.join(links), 'CARDS': ''.join(cards),
        'SHOWN': str(shown), 'FILE_CATALOG': file_catalog_html(data),
        'CURRENT': esc(current['title']), 'CURRENT_STATUS': STATUSES[current['status']],
        'CURRENT_QUESTION': esc(current.get('question', '')),
        'TRACE_KIND': esc(data.get('trace_kind', '尚未演练')),
        'AGENT_GRAPH': svg(data.get('agent_graph', {}), 'agent'), 'TRACE_JSON': encoded,
        'QUESTIONS': questions, 'VERIFICATION': esc(imp.get('verification', '尚未生成或执行代码。'))}
    return re.sub(r'__([A-Z_]+)__', lambda m: replacements[m.group(1)], page)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.state.resolve() == args.output.resolve():
        parser.error('Output must not overwrite the JSON state')
    try:
        data = json.loads(args.state.read_text(encoding='utf-8-sig'))
        page = render(data)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding='utf-8')
    print('Created: ' + str(args.output.resolve()))


if __name__ == '__main__':
    main()
