// Exercise actual render functions in an isolated document stub, not a browser.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const artifact=process.argv[2]||path.resolve(__dirname,'../examples/agent-workbench.html');
const html=fs.readFileSync(artifact,'utf8'),match=html.match(/<script id="offline-data" type="application\/json">([\s\S]*?)<\/script>/);
assert.ok(match,'An actual offline snapshot is required');
const fixture=JSON.parse(match[1]);assert.ok(fixture.structure_views);
const elements=new Map();
function element(selector){if(!elements.has(selector))elements.set(selector,{innerHTML:'',textContent:'',addEventListener(){},classList:{toggle(){}},scrollIntoView(){}});return elements.get(selector);}
element('#offline-data').textContent=JSON.stringify(fixture);
const context={document:{getElementById:id=>element('#'+id),querySelector:element},window:{addEventListener(){},scrollTo(){}},setTimeout:()=>0,clearTimeout(){},localStorage:{setItem(){},getItem(){return null}},console};
context.globalThis=context;
let source=fs.readFileSync(path.join(root,'assets/workbench/app.js'),'utf8');
source=source.replace('  boot();',`  globalThis.testStudio={setModule(id){moduleId=id;selectedNode='';},setScope(s){diagramScope=s;compareGraphs=false;},setMode(m){diagramMode=m;},setCompare(){diagramScope='overall';compareGraphs=true;},panel:diagramPanel,page:structurePage,explain:focusExplanation,inspector:nodeInspector};\n  boot();`);
vm.runInNewContext(source,context);const studio=context.testStudio;
for(const m of fixture.state.modules){studio.setModule(m.id);studio.setScope('step');assert.ok(studio.page().includes(m.title));studio.setScope('overall');assert.ok(studio.panel().includes('整体智能体流程'));}
studio.setModule('tools');studio.setScope('step');let local=studio.panel();
assert.ok(local.includes('data-node="search"'));assert.ok(!local.includes('data-node="START"'));assert.ok(local.includes('step-context'));assert.ok(local.includes('step-focus'));assert.ok(local.includes('调用 search_courses'));
studio.setScope('overall');let overall=studio.panel();assert.ok(overall.includes('data-node="START"'));assert.ok(overall.includes('step-muted'));assert.ok(overall.includes('本步最近改动'));assert.ok(overall.includes('逐节点查看输入、输出和对应实现'));
studio.setMode('components');studio.setScope('step');assert.equal((studio.panel().match(/class="component /g)||[]).length,1);studio.setScope('overall');assert.equal((studio.panel().match(/class="component /g)||[]).length,15);
studio.setMode('flow');studio.setModule('memory');studio.setScope('step');assert.ok(studio.panel().includes('本项目未接入这个结构'));assert.ok(!studio.panel().includes('data-node="validate"'));assert.ok(!studio.inspector().includes('检查输入'));
studio.setModule('prompt');studio.setScope('step');assert.ok(studio.panel().includes('data-node="answer"'));assert.ok(studio.panel().includes('配置约束这些节点'));
studio.setCompare();let compared=studio.panel();assert.ok(compared.includes('修改前'));assert.ok(!compared.includes('step-focus'));assert.ok(compared.includes('历史版本对照'));
studio.setScope('step');assert.ok(!studio.panel().includes('compare-grid'));assert.ok(studio.panel().includes('step-focus'));
console.log('15 structures render; real local/overall scope, red focus, unused state, local composition, internal flow and historical isolation passed.');
