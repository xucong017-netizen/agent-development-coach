(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const escape = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const statusNames = {pending:'待填写',active:'进行中',done:'已完成',skipped:'本次不采用',review:'需复核'};
  const presentationNames = {pending:'成果待展示',shown:'成果已展示',review:'成果需重讲'};
  const views = [['lesson','▦','结构课堂'],['files','▤','文件与代码'],['graph','◇','架构地图'],['trace','▷','运行演练'],['overview','◎','项目全貌']];
  let snapshot, draftRevision = '', draftState = null, draftFiles = new Map(), pendingSnapshot = null;
  let view='lesson', moduleId='', filePath='', fileMode='read', fileSearch='', traceIndex=0, selectedNode='', graphEditing=false;
  let connection='loading', errorMessage='', saving=false, toastTimer, updateCount=0;
  const offline = Boolean(document.getElementById('offline-data'));
  const state = () => draftState || snapshot.state;
  const dirty = () => Boolean(draftState || draftFiles.size);
  const module = () => state().modules.find(m => m.id===moduleId) || state().modules[0];
  const file = () => snapshot.files.find(f=>f.path===filePath);
  const draftKey = () => 'agent-workbench-draft:' + (snapshot.project_path || snapshot.project_name || snapshot.state.title);
  function toast(message, error=false) {
    const target=$('#toast'); target.textContent=message;target.className='visible'+(error?' error':'');
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>target.className='',5000);
  }
  function preserveDraft() {
    try {localStorage.setItem(draftKey(),JSON.stringify({state:draftState,revision:draftRevision,files:[...draftFiles],time:new Date().toISOString()}));}
    catch {toast('浏览器无法保存草稿，请使用“导出成果”保留内容。',true);}
  }
  function updateChrome() {
    const label=$('#dirty-label'); if(label)label.textContent=dirty()?'有未写入项目的草稿':'项目内容已同步';
    const banner=$('#remote-banner'); if(banner)banner.classList.toggle('hidden',!pendingSnapshot);
  }
  function editState(change) {
    if(!draftState){draftState=clone(snapshot.state);draftRevision=snapshot.revision;}
    change(draftState);preserveDraft();updateChrome();
  }
  function markAffected(s, ids) {
    for(const m of s.modules)if(ids.includes(m.id)){m.status='review';m.presentation_status='review';}
    if(s.design_status==='设计完成')s.design_status='需复核';
  }
  function code(content, selectedLine=0) {
    return '<div class="code-frame">'+String(content??'').split('\n').map((line,i)=>
      `<div class="code-line ${i+1===selectedLine?'selected':''}" id="source-line-${i+1}"><span class="ln">${i+1}</span><code>${escape(line)||' '}</code></div>`).join('')+'</div>';
  }
  function json(value) {return escape(typeof value==='string'?value:JSON.stringify(value??{},null,2));}
  function timeLabel(value) {return value?new Date(value).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'尚未读取';}
  function graph(graphData, highlight='', interactive=false, selected='') {
    const nodes=graphData?.nodes||[],edges=graphData?.edges||[];
    if(!nodes.length)return '<div class="empty">尚未设计运行节点。完成状态、节点和连线后，总图会在这里更新。</div>';
    const pos=new Map(nodes.map((n,i)=>[n.id,{x:Number(n.x??30+(i%3)*270),y:Number(n.y??35+Math.floor(i/3)*140)}]));
    const width=Math.max(...[...pos.values()].map(p=>p.x))+260, height=Math.max(...[...pos.values()].map(p=>p.y))+130;
    let out=`<svg class="agent-diagram" viewBox="0 0 ${width} ${height}" role="img" aria-label="智能体结构与数据流"><defs><marker id="arrow-${interactive?'edit':'read'}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#6c86a2"/></marker></defs>`;
    for(const e of edges){const a=pos.get(e.from),b=pos.get(e.to);if(!a||!b)continue;
      let d,lx,ly;
      if(e.from===e.to){d=`M${a.x+60} ${a.y} C${a.x+60} ${a.y-30} ${a.x+170} ${a.y-30} ${a.x+170} ${a.y}`;lx=a.x+115;ly=a.y-16;}
      else if(b.y>a.y){const sx=a.x+110,sy=a.y+76,ex=b.x+110,ey=b.y,mid=(sy+ey)/2;d=`M${sx} ${sy} C${sx} ${mid} ${ex} ${mid} ${ex} ${ey}`;lx=(sx+ex)/2;ly=mid-5;}
      else if(b.y<a.y){const side=Math.max(5,Math.min(a.x,b.x)-18);d=`M${a.x} ${a.y+38} C${side} ${a.y+38} ${side} ${b.y+38} ${b.x} ${b.y+38}`;lx=side;ly=(a.y+b.y)/2;}
      else{const sx=b.x>a.x?a.x+220:a.x,ex=b.x>a.x?b.x:b.x+220;d=`M${sx} ${a.y+38} L${ex} ${b.y+38}`;lx=(sx+ex)/2;ly=a.y+30;}
      out+=`<path d="${d}" fill="none" stroke="#8da3bb" stroke-width="1.6" marker-end="url(#arrow-${interactive?'edit':'read'})"/><text class="edge-text" x="${lx}" y="${ly}" text-anchor="middle">${escape(e.label||'')}</text>`;
    }
    for(const n of nodes){const p=pos.get(n.id),text=String(n.label||n.id),lines=text.match(/.{1,13}/gu)||[''];
      out+=`<g class="graph-node ${n.id===highlight?'current':''} ${n.id===selected?'selected':''} ${interactive?'drag':''}" data-node="${escape(n.id)}"><title>${escape(n.label||n.id)}</title><rect x="${p.x}" y="${p.y}" width="220" height="76" rx="12"/><text class="node-kind" x="${p.x+14}" y="${p.y+19}">${escape(n.kind||'节点')}</text>`;
      lines.slice(0,2).forEach((line,i)=>out+=`<text class="node-name" text-anchor="middle" x="${p.x+110}" y="${p.y+41+i*18}">${escape(line)}</text>`);out+='</g>';
    }
    return out+'</svg>';
  }
  function explanations(blocks) {
    return (blocks||[]).map(b=>`<details class="explanation" open><summary>${escape(b.block||'逻辑块')}</summary><dl>${[['why','为什么需要'],['input','输入'],['action','这段做什么'],['output','输出'],['consequence','改错会怎样'],['graph_node','对应结构']].map(([key,label])=>`<dt>${label}</dt><dd>${escape(b[key]||'尚未补充讲解')}</dd>`).join('')}</dl></details>`).join('');
  }
  function referencesNode(artifact, id) {
    if(Array.isArray(artifact.graph_nodes))return artifact.graph_nodes.includes(id);
    return (artifact.explanations||[]).some(b=>String(b.graph_node||'').trim().split(/[；;，,、\s]/)[0]===id);
  }
  function actualArtifact(artifact) {
    const current=snapshot.files.find(f=>f.path===artifact.path);
    const copy={...artifact};
    if(current?.content!=null){
      if(/完整.*文件|完整 JSON/.test(artifact.content_scope||''))copy.content=draftFiles.get(current.path)?.content??current.content;
      else {const heading=String(artifact.content||'').split('\n')[0];if(heading.startsWith('## ')&&current.content.includes(heading)){const start=current.content.indexOf(heading),next=current.content.indexOf('\n## ',start+heading.length);copy.content=current.content.slice(start,next<0?undefined:next).trimEnd()+'\n';}}
    }
    if(copy.content!=null&&String(copy.content).replace(/\r\n/g,'\n').trim()!==String(artifact.content||'').replace(/\r\n/g,'\n').trim())copy.outdated=true;
    return copy;
  }
  function artifactCard(original) {
    const a=actualArtifact(original),v=a.verification||{},isCode=String(a.path).endsWith('.py')||a.kind==='业务代码';
    return `<article class="artifact"><div class="artifact-head"><div><h3>${escape(a.path||'本步成果')}</h3><p class="muted">${escape(a.purpose||'')}</p></div><button class="btn small" data-open-file="${escape(a.path)}">查看文件</button></div><p class="muted">${escape(a.kind)} · ${escape(a.content_scope||'实际内容')}</p>${a.outdated?'<div class="callout warning">文件已改变。下方正文已尽可能读取最新内容，原讲解与检查需要 WorkBuddy 复核。</div>':''}${isCode?`<div class="code-lesson"><div class="code-column">${code(a.content)}</div><div class="explanation-column">${explanations(a.explanations)}</div></div>`:`<div class="prose">${escape(a.content||'尚未记录正文')}</div>${explanations(a.explanations)}`}<div class="panel-head"><h3>检查与结果</h3><span class="badge">${escape(a.outdated?'旧版本结果 · 待复核':v.status||'未执行')}</span></div><p class="muted">命令：<code>${escape(v.command||'尚未记录')}</code></p><div class="check-grid"><div class="check-result"><b>预期</b><p>${escape(v.expected||'尚未定义')}</p></div><div class="check-result"><b>实际结果</b><pre>${escape(v.actual||'未执行。这里不会把预期结果当成真实输出。')}</pre></div></div></article>`;
  }
  function fileRows(paths) {
    return paths.map(path=>{const f=snapshot.files.find(x=>x.path===path),a=state().modules.flatMap(m=>m.artifacts||[]).find(x=>x.path===path);
      return `<div class="file-row"><span class="file-type">${escape(path.split('.').pop().toUpperCase())}</span><div><button class="text-btn" data-open-file="${escape(path)}"><code>${escape(path)}</code></button><p>${escape(f?.purpose||a?.purpose||'职责尚未登记，可在“文件与代码”中补充。')}</p><p>调用：${escape(f?.caller||'尚未登记')}</p></div></div>`;}).join('');
  }
  function lessonView() {
    const m=module(),index=state().modules.indexOf(m),artifacts=m.artifacts||[],paths=[...new Set(artifacts.map(a=>a.path))];
    return `<div class="page-intro"><div><div class="eyebrow">结构课堂 · ${String(index+1).padStart(2,'0')} / 15</div><h1>${escape(m.title)}</h1><p>看清这个结构的职责、文件和具体成果。</p></div><div class="status-group"><span class="badge ${escape(m.status)}">${statusNames[m.status]}</span><span class="badge ${escape(m.presentation_status||'pending')}">${presentationNames[m.presentation_status||'pending']}</span></div></div>
    <label class="field" for="module-picker">选择教学结构</label><select class="input module-picker" id="module-picker">${state().modules.map(x=>`<option value="${escape(x.id)}" ${x.id===moduleId?'selected':''}>${escape(x.title)}</option>`).join('')}</select><div class="lesson-layout"><div><section class="panel"><h2>这个结构做什么</h2><p class="purpose">${escape(m.purpose)}</p><div class="structure-list">${String(m.parts||'').split(/[、，]/).filter(Boolean).map(p=>`<span>${escape(p)}</span>`).join('')}</div><div class="diagram-box">${graph(m.graph)}</div><p class="muted">${escape(m.graph_kind||'教学示意')} · 完整运行架构见“架构地图”</p></section>
</div>
    <div><section class="panel"><h2>本步设计 · 可以改</h2><label class="field" for="module-decision">当前决定</label><textarea class="input" id="module-decision" data-edit="decision">${escape(m.decision||'')}</textarea><label class="field" for="module-note">学习笔记</label><textarea class="input" id="module-note" data-edit="notes" placeholder="记下疑问、自己的理解或需要 WorkBuddy 修改的地方。">${escape(m.notes||'')}</textarea><div class="button-row"><button class="btn primary" data-action="save">${offline?'保存本机草稿':'保存设计'}</button></div><p class="muted">修改决定会标记后续结构需复核；不会自动改业务代码。</p></section>
    <section class="panel"><h2>这一步有哪些文件</h2>${paths.length?fileRows(paths):'<p class="muted">尚未登记本步文件。进度记录不是正文或业务代码的替代品。</p>'}</section>
    <section class="panel"><h2>检查理解</h2><div class="callout">${escape(m.question||'')}</div><p>${escape(m.check||m.acceptance||'尚未定义检查')}</p><div class="button-row"><button class="btn" data-action="previous-module" ${index===0?'disabled':''}>上一结构</button><button class="btn" data-action="next-module" ${index===state().modules.length-1?'disabled':''}>浏览下一结构</button></div><p class="muted">浏览不改变学员完成状态；实际授课仍由 Skill 按步检查。</p></section></div></div>    <section class="panel"><div class="panel-head"><h2>实际成果与逐段讲解</h2><button class="btn small" data-action="mark-shown" ${!artifacts.length?'disabled':''}>记录为已讲解</button></div>${artifacts.length?artifacts.map(artifactCard).join(''):'<div class="empty">本步尚未记录正文或代码。让 WorkBuddy 更新 artifacts，写入内容、文件用途和代码解释；项目已有文件仍可从“文件与代码”查看。</div>'}</section>`;
  }
  function filesView() {
    const f=file(),current=f?draftFiles.get(f.path)?.content??f.content??'':'',allArtifacts=state().modules.flatMap(m=>m.artifacts||[]).filter(a=>a.path===filePath);
    const list=snapshot.files.filter(f=>f.path.toLowerCase().includes(fileSearch.toLowerCase()));
    return `<div class="page-intro"><div><div class="eyebrow">项目文件</div><h1>文件与代码</h1><p>直接查看实际文件；保存后让 WorkBuddy 复核相关讲解。</p></div></div><div class="files-layout"><section class="panel file-browser"><label class="field" for="file-search">搜索文件</label><input class="input" id="file-search" value="${escape(fileSearch)}" placeholder="文件名或目录"><div class="file-list">${list.map(x=>`<button data-file="${escape(x.path)}" class="${x.path===filePath?'active':''}">${escape(x.path)} ${draftFiles.has(x.path)?'•':''}</button>`).join('')}</div><p class="muted">${snapshot.files.length} 个实际文本文件</p></section><div>${f?`<section class="panel"><div class="panel-head"><div><h2>${escape(f.path)}</h2><p class="muted">${escape(f.purpose||'尚未登记用途')} · ${Math.ceil(f.size/1024)} KB</p></div><div class="actions"><button class="btn" data-action="download-file">导出文件</button><button class="btn primary" data-action="save" ${!f.editable?'disabled':''}>${offline?'保存本机草稿':'保存改动'}</button></div></div><div class="section-tabs"><button data-file-mode="read" class="${fileMode==='read'?'active':''}">阅读内容</button><button data-file-mode="edit" class="${fileMode==='edit'?'active':''}" ${!f.editable?'disabled':''}>编辑内容</button><button data-file-mode="explain" class="${fileMode==='explain'?'active':''}">用途与讲解</button></div>${f.notice?`<div class="callout warning">${escape(f.notice)}</div>`:''}${f.syntax_notice?`<div class="callout warning">${escape(f.syntax_notice)}</div>`:''}
      ${fileMode==='read'?`${(f.symbols||[]).length?`<div class="symbol-list">${f.symbols.map(s=>`<button data-symbol="${s.start}">${escape(s.name)} · ${s.start}–${s.end}</button>`).join('')}</div>`:''}${code(current)}`:fileMode==='edit'?`<label class="field" for="file-editor">实际文件内容</label><textarea class="code-editor" id="file-editor" spellcheck="false" wrap="off">${escape(current)}</textarea><p class="muted">保存前检查当前文件；工作台不自动执行代码。同步模式会备份原文件。</p>`:`<label class="field" for="file-purpose">文件职责</label><textarea class="input" id="file-purpose" data-file-meta="purpose">${escape((state().file_catalog||[]).find(c=>c.path===f.path)?.purpose||f.purpose||'')}</textarea><label class="field" for="file-caller">谁调用它</label><input class="input" id="file-caller" data-file-meta="caller" value="${escape((state().file_catalog||[]).find(c=>c.path===f.path)?.caller||f.caller||'')}"><div class="button-row"><button class="btn primary" data-action="save">保存用途说明</button></div><h3 style="margin-top:22px">已有代码讲解</h3>${allArtifacts.length?allArtifacts.map(a=>explanations(a.explanations)).join(''):'<p class="muted">尚未记录逐段解释。请让 WorkBuddy 根据此文件补讲，并更新本步 artifacts。</p>'}${(f.symbols||[]).map(s=>`<div class="callout"><b>${escape(s.kind)} ${escape(s.name)}</b><p>${escape(s.doc||'代码中没有说明文字，需要补充教学解释。')}</p></div>`).join('')}`}</section>`:'<section class="panel"><div class="empty">项目尚无可展示文件。</div></section>'}</div></div>`;
  }
  function graphView() {
    const g=state().agent_graph||{nodes:[],edges:[]},n=g.nodes.find(n=>n.id===selectedNode)||g.nodes[0];if(n&&!selectedNode)selectedNode=n.id;
    return `<div class="page-intro"><div><div class="eyebrow">业务流程与结构</div><h1>架构地图</h1><p>点击节点看职责；编辑图不会自动生成或运行对应代码。</p></div><div class="actions"><button class="btn" data-action="toggle-graph-edit">${graphEditing?'结束图编辑':'编辑节点与连线'}</button>${graphEditing?'<button class="btn primary" data-action="save">保存架构</button>':''}</div></div><div class="graph-editor"><section class="panel"><div class="panel-head"><h2>完整运行图</h2><span class="badge">${g.nodes.length} 个节点 · ${g.edges.length} 条连线</span></div><div class="diagram-box" id="editable-graph">${graph(g,'',graphEditing,selectedNode)}</div>${graphEditing?'<p class="muted">可以拖动节点调整位置，也可在右侧填写坐标。改动只存在草稿中，保存后写回进度并标记相关结构需复核。</p>':''}<div class="table-wrap"><table><thead><tr><th>来源</th><th>去向</th><th>条件</th>${graphEditing?'<th>操作</th>':''}</tr></thead><tbody>${g.edges.map((e,i)=>`<tr><td>${escape(e.from)}</td><td>${escape(e.to)}</td><td>${graphEditing?`<input class="input" data-edge-label="${i}" value="${escape(e.label||'')}">`:escape(e.label||'固定连线')}</td>${graphEditing?`<td><button class="text-btn" data-remove-edge="${i}">移除</button></td>`:''}</tr>`).join('')}</tbody></table></div></section><section class="panel node-card"><h2>${n?'节点详情':'新增节点'}</h2>${n?`<div><label class="field">节点 ID</label><div class="prose">${escape(n.id)}</div></div><div><label class="field" for="node-label">名称</label><input class="input" id="node-label" data-node-field="label" value="${escape(n.label||n.id)}" ${!graphEditing?'readonly':''}></div><div><label class="field" for="node-kind">职责类型</label><input class="input" id="node-kind" data-node-field="kind" value="${escape(n.kind||'节点')}" ${!graphEditing?'readonly':''}></div>${graphEditing?`<div><label class="field">位置 x / y</label><div class="two-col"><input class="input" aria-label="节点 x 坐标" type="number" min="0" max="10000" data-node-field="x" value="${n.x??30}"><input class="input" aria-label="节点 y 坐标" type="number" min="0" max="10000" data-node-field="y" value="${n.y??35}"></div></div>`:''}<div><label class="field">相关源文件</label><p class="muted">${escape(state().modules.flatMap(m=>m.artifacts||[]).filter(a=>referencesNode(a,n.id)).map(a=>a.path).filter((x,i,a)=>a.indexOf(x)===i).join('；')||'尚未登记文件对应关系。')}</p></div>`:''}${graphEditing?`<div class="button-row"><button class="btn" data-action="add-node">新增节点</button>${n?'<button class="btn danger" data-action="remove-node">移除此节点</button>':''}</div><div><label class="field" for="edge-from">连接来源</label><select class="input" id="edge-from">${g.nodes.map(x=>`<option value="${escape(x.id)}">${escape(x.label||x.id)}</option>`).join('')}</select></div><div><label class="field" for="edge-to">连接去向</label><select class="input" id="edge-to">${g.nodes.map(x=>`<option value="${escape(x.id)}">${escape(x.label||x.id)}</option>`).join('')}</select></div><div><label class="field" for="edge-condition">条件标签</label><input class="input" id="edge-condition" placeholder="如：资料存在"></div><div class="button-row"><button class="btn" data-action="add-edge">添加连线</button></div>`:''}</section></div>`;
  }
  function traceView() {
    const traces=state().trace||[],t=traces[traceIndex],accumulated={};
    const run=t?.run;for(let i=0;i<=traceIndex;i++)if(traces[i]&&traces[i].run===run&&typeof traces[i].update==='object')Object.assign(accumulated,traces[i].update);
    return `<div class="page-intro"><div><div class="eyebrow">可观察的执行过程</div><h1>运行演练</h1><p>${escape(state().trace_kind||'尚未记录轨迹')} · 回放不会执行代码或调用模型。</p></div></div>${t?`<div class="trace-nav"><button class="btn" data-action="trace-prev" ${traceIndex===0?'disabled':''}>上一步</button><button class="btn primary" data-action="trace-next" ${traceIndex===traces.length-1?'disabled':''}>下一步</button><span class="muted">${traceIndex+1} / ${traces.length} · ${escape(t.run||'当前请求')}</span></div><div class="trace-steps">${traces.map((x,i)=>`<button class="${i===traceIndex?'active':''}" data-trace="${i}">${escape(x.node)} · ${x.step}</button>`).join('')}</div><div class="two-col"><section class="panel"><h2>当前节点：${escape(t.node)}</h2><div class="diagram-box">${graph(state().agent_graph,t.node)}</div></section><div><section class="panel"><h2>本步输入与更新</h2><div class="check-grid"><div class="check-result"><b>输入</b><pre>${json(t.input)}</pre></div><div class="check-result"><b>状态更新</b><pre>${json(t.update)}</pre></div></div><h3 style="margin-top:16px">可见输出</h3><div class="prose">${json(t.output)}</div><p><b>依据：</b>${escape(t.basis||'尚未记录')}</p></section><section class="panel"><h2>本条轨迹已累计的更新</h2><div class="prose">${json(accumulated)}</div><p class="muted">只汇总已保存更新，不代表完整状态快照。</p></section></div></div>`:'<section class="panel"><div class="empty">尚未演练。让 WorkBuddy 记录正常和异常请求的节点、输入、更新、输出及依据。</div></section>'}`;
  }
  function overviewView() {
    const s=state(),complete=s.modules.filter(m=>['done','skipped'].includes(m.status)).length,shown=s.modules.filter(m=>m.presentation_status==='shown').length;
    return `<div class="page-intro"><div><div class="eyebrow">项目全貌</div><h1>成果、进度与待办</h1><p>学习进度、设计决定、实际文件和运行状态分别查看。</p></div></div><div class="metrics"><div class="metric"><strong>${complete}/15</strong><span>结构已有决定</span></div><div class="metric"><strong>${shown}/15</strong><span>成果已展示</span></div><div class="metric"><strong>${snapshot.files.length}</strong><span>实际文本文件</span></div><div class="metric"><strong>${(s.trace||[]).length}</strong><span>已保存轨迹步骤</span></div></div><div class="two-col"><section class="panel"><h2>已确定的设计</h2><div class="key-values">${Object.entries(s.decisions||{}).map(([k,v])=>`<b>${escape(k)}</b><span>${json(v)}</span>`).join('')||'<span>尚未记录整体决定。</span>'}</div><h3 style="margin-top:20px">设计与代码状态</h3><p>${escape(s.design_status||'进行中')} · ${escape(s.implementation?.status||'未开始')}</p><div class="callout">${escape(s.implementation?.verification||'尚未记录实际执行证据。')}</div></section><section class="panel"><h2>未决项</h2>${(s.open_questions||[]).length?`<ul>${s.open_questions.map(q=>`<li>${escape(q)}</li>`).join('')}</ul>`:'<p class="muted">没有已记录待办，完成前仍需检查。</p>'}<h3 style="margin-top:20px">网页保存记录</h3><div class="timeline">${(snapshot.activity||[]).slice().reverse().slice(0,12).map(a=>`<article><time>${timeLabel(a.time)}</time><div>${escape(a.action)}</div><div class="activity-path muted">${escape(a.path)}</div></article>`).join('')||'<p class="muted">暂无网页写入记录。WorkBuddy 的文件更新会自动读取，但不会伪造为网页操作。</p>'}</div></section></div><section class="panel"><h2>全部实际文件与职责</h2><div class="table-wrap"><table><thead><tr><th>文件</th><th>功能</th><th>调用关系</th><th>大小</th></tr></thead><tbody>${snapshot.files.map(f=>`<tr><td><button class="text-btn" data-open-file="${escape(f.path)}">${escape(f.path)}</button></td><td>${escape(f.purpose||'尚未登记')}</td><td>${escape(f.caller||'尚未登记')}</td><td>${Math.ceil(f.size/1024)} KB</td></tr>`).join('')}</tbody></table></div></section><section class="panel"><div class="panel-head"><h2>完整进度数据 · 可编辑</h2><button class="btn primary" data-action="apply-json">应用 JSON 到草稿</button></div><label class="field" for="state-json">teaching-state.json</label><textarea class="code-editor full-json" id="state-json" spellcheck="false">${escape(JSON.stringify(s,null,2))}</textarea><p class="muted">用于查看或修改全部已记录信息。应用后仍需保存；结构错误会被服务端拒绝，草稿保留。</p></section>`;
  }
  function render() {
    if(!snapshot)return;
    const s=state();
    const connectionText=offline?'离线副本 · 本机草稿':connection==='error'?'连接待恢复':'本地同步 · 自动刷新';
    $('#app').innerHTML=`<div class="shell"><aside class="sidebar"><div class="brand"><div class="brand-mark">A</div><div><strong>智能体教学工作台</strong><small>从结构到看得见的成果</small></div></div><nav class="view-nav" aria-label="工作台视图">${views.map(([id,icon,label])=>`<button data-view="${id}" class="${view===id?'active':''}"><span class="nav-icon">${icon}</span>${label}</button>`).join('')}</nav><div class="nav-group">15 个开发结构</div><nav class="lesson-nav" aria-label="课程结构">${s.modules.map((m,i)=>`<button data-module="${escape(m.id)}" class="${m.id===moduleId?'active ':''}${escape(m.status)}"><span class="index">${String(i+1).padStart(2,'0')}</span><span>${escape(m.title)}</span><span class="dot"></span></button>`).join('')}</nav><p class="sidebar-note">${offline?'离线编辑保存在浏览器草稿。启动本地服务后，才能直接写回项目文件。':'WorkBuddy 写入项目后，这里会自动发现新成果。网页保存有备份，代码不会自动执行。'}</p></aside><div class="workspace"><header class="topbar"><div><div class="project-title">${escape(s.title||'我的智能体项目')}</div><div class="top-meta"><span class="connection ${offline?'offline':connection==='error'?'error':''}">${connectionText}</span><span>读取于 ${timeLabel(snapshot.server_time)}</span><span class="dirty-label" id="dirty-label">${dirty()?'有未写入项目的草稿':'项目内容已同步'}</span></div></div><div class="actions"><button class="btn" data-action="refresh">读取最新</button><button class="btn" data-action="export">导出成果</button><label class="btn import-label">导入进度<input class="hidden" id="import-state" type="file" accept=".json"></label><button class="btn primary" data-action="save" ${saving?'disabled':''}>${saving?'正在保存…':offline?'保存本机草稿':'保存草稿'}</button></div></header><div class="conflict ${pendingSnapshot?'':'hidden'}" id="remote-banner"><span>项目有新成果，当前编辑已保留为本机草稿。</span><button class="btn small" data-action="refresh">保留草稿并读取最新</button><button class="btn small" data-action="export">导出当前草稿</button></div><main>${connection==='error'?`<div class="callout warning">${escape(errorMessage)}</div>`:''}${view==='lesson'?lessonView():view==='files'?filesView():view==='graph'?graphView():view==='trace'?traceView():overviewView()}<div class="bottom-note">${offline?'独立 HTML 副本 · 所有编辑只形成浏览器草稿，导出后可交给 WorkBuddy。':'项目：'+escape(snapshot.project_path||snapshot.project_name)+' · 每 2.5 秒检查成果；有编辑草稿时不会覆盖输入。'}</div></main></div></div>`;
    const actions=$('.topbar .actions');
    let stored;try{stored=JSON.parse(localStorage.getItem(draftKey())||'null');}catch{}
    if(stored&&(stored.state||(stored.files||[]).length))actions?.insertAdjacentHTML('beforeend','<button class="btn small" data-action="restore-draft">恢复本机草稿</button>');
    if(dirty())actions?.insertAdjacentHTML('beforeend','<button class="btn small" data-action="discard-draft">放弃当前草稿</button>');
    wireGraphDrag();
  }
  function download(name, content, type='application/json') {
    const link=document.createElement('a');const url=URL.createObjectURL(new Blob([content],{type}));link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function exportAll() {
    const data=clone(snapshot);data.state=clone(state());delete data.token;delete data.project_path;
    for(const f of data.files)if(draftFiles.has(f.path))f.content=draftFiles.get(f.path).content;
    data.export_kind='workbench-snapshot-with-drafts';
    download('agent-workbench-snapshot.json',JSON.stringify(data,null,2));toast('成果与当前草稿已导出。');
  }
  async function post(url, body) {
    const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-Workbench-Token':snapshot.token},body:JSON.stringify(body)});
    const data=await response.json();if(!response.ok)throw new Error(data.error||'保存失败');return data;
  }
  async function save() {
    if(saving)return;
    if(!dirty()){toast('没有待保存改动。');return;}
    if(offline){preserveDraft();toast('已保存本机浏览器草稿；未写回项目文件。可导出成果交给 WorkBuddy。');return;}
    saving=true;updateChrome();
    try {
      if(draftState){const saved=await post('/api/state',{state:draftState,expected_revision:draftRevision||snapshot.revision});draftState=null;draftRevision='';snapshot=saved;}
      for(const [path,draft] of [...draftFiles]){const saved=await post('/api/file',{path,content:draft.content,expected_sha:draft.sha});draftFiles.delete(path);snapshot=saved;}
      pendingSnapshot=null;preserveDraft();connection='ready';toast('已写回项目文件，原内容已备份。相关代码讲解需复核。');render();
    } catch(error){preserveDraft();toast(error.message,true);}finally{saving=false;updateChrome();}
  }
  async function readLatest(manual=false) {
    if(saving)return;
    if(offline){if(manual)toast('独立 HTML 是成果副本。请启动本地工作台读取实时项目，或导入更新的进度 JSON。');return;}
    try {
      const response=await fetch('/api/snapshot'+(!manual&&snapshot?'?revision='+encodeURIComponent(snapshot.revision):''),{cache:'no-store'});
      const data=await response.json();if(!response.ok)throw new Error(data.error||'读取失败');
      if(data.unchanged){if(connection==='error'){connection='ready';render();}return;}
      connection='ready';errorMessage='';
      if(snapshot&&dirty()&&!manual){pendingSnapshot=data;updateChrome();return;}
      if(manual&&dirty()){preserveDraft();draftState=null;draftRevision='';draftFiles=new Map();toast('已读取最新成果；之前的草稿保留在本机，可用“恢复本机草稿”取回。');}
      snapshot=data;pendingSnapshot=null;updateCount++;if(!moduleId||!snapshot.state.modules.some(m=>m.id===moduleId))moduleId=snapshot.state.current_module||snapshot.state.modules[0].id;
      if(!filePath||!snapshot.files.some(f=>f.path===filePath))filePath=snapshot.files.find(f=>f.path.endsWith('tools.py'))?.path||snapshot.files[0]?.path||'';
      traceIndex=Math.min(traceIndex,Math.max(0,(state().trace||[]).length-1));render();
      if(manual)toast('已读取最新成果。');
    }catch(error){connection='error';errorMessage='读取项目失败：'+error.message+'。保持本地服务运行，已有草稿不会丢失。';if(snapshot)render();else $('#app').innerHTML=`<div class="loading"><strong>项目暂时无法读取</strong><p>${escape(errorMessage)}</p><button class="btn" data-action="refresh">重新读取</button></div>`;}
  }
  function wireGraphDrag() {
    if(!graphEditing||view!=='graph')return;
    const svg=$('#editable-graph svg');if(!svg)return;
    svg.addEventListener('pointerdown',event=>{const group=event.target.closest('[data-node]');if(!group)return;const id=group.dataset.node;selectedNode=id;
      const toPoint=e=>{const p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;return p.matrixTransform(svg.getScreenCTM().inverse());};
      const start=toPoint(event),node=state().agent_graph.nodes.find(n=>n.id===id);if(!node)return;
      const origin={x:Number(node.x??30),y:Number(node.y??35)};let moved=false,position=origin;
      svg.setPointerCapture(event.pointerId);
      const move=e=>{const p=toPoint(e);position={x:Math.max(0,Math.min(10000,Math.round(origin.x+p.x-start.x))),y:Math.max(0,Math.min(10000,Math.round(origin.y+p.y-start.y)))};moved=Math.abs(p.x-start.x)+Math.abs(p.y-start.y)>3;group.setAttribute('transform',`translate(${position.x-origin.x},${position.y-origin.y})`);};
      const up=()=>{svg.removeEventListener('pointermove',move);svg.removeEventListener('pointerup',up);if(moved)editState(s=>{Object.assign(s.agent_graph.nodes.find(n=>n.id===id),position);markAffected(s,['nodes','edges','routing','evaluation','delivery']);});render();};
      svg.addEventListener('pointermove',move);svg.addEventListener('pointerup',up,{once:true});
    });
  }
  $('#app').addEventListener('click',async event=>{
    const target=event.target.closest('button,[data-node]');if(!target)return;
    if(target.dataset.view){view=target.dataset.view;render();return;}
    if(target.dataset.module){moduleId=target.dataset.module;view='lesson';render();return;}
    if(target.dataset.file||target.dataset.openFile){const path=target.dataset.file||target.dataset.openFile;if(!snapshot.files.some(f=>f.path===path)){toast('这个文件尚未在当前项目创建。',true);return;}filePath=path;view='files';fileMode='read';render();return;}
    if(target.dataset.fileMode){fileMode=target.dataset.fileMode;render();return;}
    if(target.dataset.symbol){const line=$('#source-line-'+target.dataset.symbol);line?.scrollIntoView({block:'center',behavior:'smooth'});return;}
    if(target.dataset.trace!=null){traceIndex=Number(target.dataset.trace);render();return;}
    if(target.dataset.node){selectedNode=target.dataset.node;if(view==='graph'&&!graphEditing)render();return;}
    if(target.dataset.removeEdge!=null){editState(s=>{s.agent_graph.edges.splice(Number(target.dataset.removeEdge),1);markAffected(s,['edges','routing','evaluation','delivery']);});render();return;}
    const action=target.dataset.action;
    if(action==='restore-draft'){try{const d=JSON.parse(localStorage.getItem(draftKey()));draftState=d.state;draftRevision=d.revision||snapshot.revision;draftFiles=new Map(d.files||[]);render();toast('本机草稿已恢复，保存前核对项目是否已变化。');}catch(error){toast(error.message,true);}return;}
    if(action==='discard-draft'){draftState=null;draftRevision='';draftFiles=new Map();preserveDraft();if(pendingSnapshot){snapshot=pendingSnapshot;pendingSnapshot=null;}render();toast('已放弃当前草稿，项目文件未改变。');return;}
    if(action==='save')return save();
    if(action==='refresh')return readLatest(true);
    if(action==='export')return exportAll();
    if(action==='previous-module'||action==='next-module'){const i=state().modules.findIndex(m=>m.id===moduleId);moduleId=state().modules[i+(action==='next-module'?1:-1)].id;render();return;}
    if(action==='mark-shown'){editState(s=>s.modules.find(m=>m.id===moduleId).presentation_status='shown');render();toast('已记为讲解草稿；保存后更新进度。');return;}
    if(action==='download-file'){const f=file();if(f)download(f.path.split('/').pop(),draftFiles.get(f.path)?.content??f.content??'','text/plain;charset=utf-8');return;}
    if(action==='toggle-graph-edit'){graphEditing=!graphEditing;render();return;}
    if(action==='add-node'){const id='node_'+Date.now().toString(36);editState(s=>{s.agent_graph ||= {nodes:[],edges:[]};s.agent_graph.nodes.push({id,label:'新工作节点',kind:'待定义',x:40,y:50+s.agent_graph.nodes.length*110});markAffected(s,['nodes','edges','routing','evaluation','delivery']);});selectedNode=id;render();return;}
    if(action==='remove-node'){editState(s=>{s.agent_graph.nodes=s.agent_graph.nodes.filter(n=>n.id!==selectedNode);s.agent_graph.edges=s.agent_graph.edges.filter(e=>e.from!==selectedNode&&e.to!==selectedNode);s.trace=(s.trace||[]).filter(t=>t.node!==selectedNode);markAffected(s,['nodes','edges','routing','evaluation','delivery']);});selectedNode='';render();return;}
    if(action==='add-edge'){const from=$('#edge-from').value,to=$('#edge-to').value,label=$('#edge-condition').value;if(from&&to){editState(s=>{s.agent_graph.edges.push({from,to,label});markAffected(s,['edges','routing','evaluation','delivery']);});render();}return;}
    if(action==='trace-prev'||action==='trace-next'){traceIndex+=action==='trace-next'?1:-1;render();return;}
    if(action==='apply-json'){try{const s=JSON.parse($('#state-json').value);if(!Array.isArray(s.modules)||s.modules.length!==15)throw new Error('需要保留 15 个结构模块。');draftState=s;draftRevision=snapshot.revision;preserveDraft();render();toast('JSON 已应用到草稿，保存后才写入项目。');}catch(error){toast('JSON 无法应用：'+error.message,true);}return;}
  });
  $('#app').addEventListener('input',event=>{
    const target=event.target;
    if(target.dataset.edit){editState(s=>{const m=s.modules.find(x=>x.id===moduleId);m[target.dataset.edit]=target.value;if(target.dataset.edit==='decision'){m.status='review';m.presentation_status='review';const index=s.modules.indexOf(m);markAffected(s,s.modules.slice(index+1).map(x=>x.id));}});return;}
    if(target.id==='file-editor'){const f=file();draftFiles.set(f.path,{content:target.value,sha:draftFiles.get(f.path)?.sha||f.sha});preserveDraft();updateChrome();return;}
    if(target.id==='file-search'){fileSearch=target.value;const position=target.selectionStart;render();$('#file-search').focus();$('#file-search').setSelectionRange(position,position);return;}
    if(target.dataset.fileMeta){editState(s=>{s.file_catalog ||= [];let item=s.file_catalog.find(x=>x.path===filePath);if(!item){item={path:filePath,kind:'项目文件',status:'已有'};s.file_catalog.push(item);}item[target.dataset.fileMeta]=target.value;});return;}
    if(target.dataset.nodeField){const key=target.dataset.nodeField,value=['x','y'].includes(key)?Math.max(0,Math.min(10000,Number(target.value))):target.value;editState(s=>{const n=s.agent_graph.nodes.find(n=>n.id===selectedNode);if(n)n[key]=value;markAffected(s,['nodes','edges','routing','evaluation','delivery']);});return;}
    if(target.dataset.edgeLabel!=null){editState(s=>{s.agent_graph.edges[Number(target.dataset.edgeLabel)].label=target.value;markAffected(s,['edges','routing','evaluation','delivery']);});}
  });
  $('#app').addEventListener('change',async event=>{
    if(event.target.id==='module-picker'){moduleId=event.target.value;render();return;}
    if(event.target.id==='import-state'&&event.target.files[0]){try{const parsed=JSON.parse(await event.target.files[0].text()),s=parsed.state||parsed;if(!Array.isArray(s.modules)||s.modules.length!==15)throw new Error('文件不是完整课程进度。');draftState=s;draftRevision=snapshot.revision;preserveDraft();render();toast('进度已导入为草稿。核对后保存，不会立即覆盖项目。');}catch(error){toast(error.message,true);}}
  });
  window.addEventListener('beforeunload',event=>{if(dirty()&&!offline){event.preventDefault();event.returnValue='';}});
  async function boot(){
    if(offline){snapshot=JSON.parse($('#offline-data').textContent);moduleId=snapshot.state.current_module||snapshot.state.modules[0].id;filePath=snapshot.files.find(f=>f.path.endsWith('tools.py'))?.path||snapshot.files[0]?.path||'';connection='offline';render();}
    else {await readLatest();setInterval(()=>readLatest(),2500);}

  }
  boot();
})();
