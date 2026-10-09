#!/usr/bin/env python3
"""Local agent teaching workbench. No third-party Python dependencies."""
import argparse
import ast
import hashlib
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import uuid
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from render_board import validate
from design_engine import normalize, reconcile, derived, audit, grade, affect, fingerprint, execution_hash, design_change_hash, change_record

VERSION = '1.5.0'
TEXT_EXTENSIONS = {'.py', '.md', '.json', '.yaml', '.yml', '.txt', '.mmd', '.html',
                   '.css', '.js', '.ts', '.tsx', '.jsx', '.toml', '.ini', '.csv', '.bat', '.ps1'}
EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.workbench'}
MAX_FILE = 2 * 1024 * 1024
MAX_BODY = 8 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bundle_fingerprint():
    root = Path(__file__).resolve().parents[1]
    files = [root / 'scripts' / n for n in ('workbench.py', 'render_board.py', 'design_engine.py', 'run_design.py')]
    files += sorted((root / 'assets' / 'workbench').glob('*'))
    return digest(b''.join(p.read_bytes() for p in files if p.is_file()))


class Conflict(Exception):
    pass


class Project:
    def __init__(self, root):
        self.root = root.resolve()
        self.state_path = self.path('agent-design/teaching-state.json')
        self.lock = threading.RLock()
        if not self.state_path.is_file():
            raise ValueError('项目需要 agent-design/teaching-state.json；先让 Skill 初始化项目。')
        self.state()

    def path(self, relative):
        if not isinstance(relative, str) or not relative or '\\' in relative:
            raise ValueError('请使用项目内的相对路径。')
        parts = Path(relative).parts
        if Path(relative).is_absolute() or '..' in parts or any(p in EXCLUDED or p.startswith('.') for p in parts):
            raise ValueError('该路径不在可编辑项目文件范围。')
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root) or target.suffix.lower() not in TEXT_EXTENSIONS:
            raise ValueError('仅支持项目内的文本文件。')
        return target

    def state(self):
        self.state_path = self.path('agent-design/teaching-state.json')
        state = json.loads(self.state_path.read_text(encoding='utf-8-sig'))
        validate({**state, 'design_status': '进行中'})
        baseline = self.root / '.workbench' / 'last-design.json'
        previous = json.loads(baseline.read_text(encoding='utf-8')) if baseline.exists() else None
        state = normalize(state, previous)
        if state.get('design_status') == '设计完成' and not audit(state, self.root)['passed']:
            state['design_status'] = '需复核'
        return state

    def files(self, state):
        catalog = {f.get('path'): f for f in state.get('file_catalog', [])}
        results = []
        for directory, folders, names in os.walk(self.root, followlinks=False):
            folders[:] = sorted(f for f in folders if f not in EXCLUDED and not f.startswith('.')
                                and not (Path(directory) / f).is_symlink()
                                and (Path(directory) / f).resolve().is_relative_to(self.root))
            for name in sorted(names):
                if name.startswith('.'):
                    continue
                source = Path(directory) / name
                if source.is_symlink() or not source.resolve().is_relative_to(self.root) or source.suffix.lower() not in TEXT_EXTENSIONS:
                    continue
                relative = source.relative_to(self.root).as_posix()
                meta = catalog.get(relative, {})
                info = {'path': relative, 'purpose': meta.get('purpose', ''),
                        'caller': meta.get('caller', ''), 'kind': meta.get('kind', ''),
                        'size': source.stat().st_size, 'modified': source.stat().st_mtime,
                        'editable': source.stat().st_size <= MAX_FILE, 'symbols': []}
                if info['editable']:
                    raw = source.read_bytes()
                    try:
                        info['content'] = raw.decode('utf-8-sig')
                        info['sha'] = digest(raw)
                    except UnicodeDecodeError:
                        info['editable'] = False
                        info['notice'] = '此文件不是 UTF-8 文本，保留原文件。'
                else:
                    info['notice'] = '文件超过 2 MB，工作台显示元信息；请用编辑器查看原文件。'
                if source.suffix == '.py' and info.get('content'):
                    try:
                        tree = ast.parse(info['content'])
                        info['symbols'] = [{'name': node.name,
                            'kind': '类' if isinstance(node, ast.ClassDef) else '函数',
                            'start': node.lineno, 'end': node.end_lineno,
                            'doc': ast.get_docstring(node) or ''} for node in tree.body
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
                    except SyntaxError as error:
                        info['syntax_notice'] = f'第 {error.lineno} 行语法待检查：{error.msg}'
                if relative in derived(state):
                    info['editable'] = False
                    info['notice'] = '由当前设计自动生成。请在设计结构或结构图修改，再保存同步。'
                results.append(info)
        return results

    def snapshot(self):
        with self.lock:
            state = self.state()
            files = self.files(state)
            fingerprints = [(f['path'], f.get('sha', str(f['modified']) + str(f['size']))) for f in files]
            revision = digest(json.dumps(fingerprints, sort_keys=True).encode())
            log = self.root / '.workbench' / 'activity.jsonl'
            activities = []
            if log.exists():
                for line in log.read_text(encoding='utf-8').splitlines()[-60:]:
                    try:
                        activities.append(json.loads(line))
                    except ValueError:
                        continue
            return {'state': state, 'files': files, 'revision': revision,
                    'project_name': self.root.name, 'project_path': str(self.root),
                    'server_time': datetime.now().astimezone().isoformat(), 'activity': activities,
                    'audit': audit(state, self.root),
                    'sync_status': {name: ((self.root / name).is_file() and (self.root / name).read_text(encoding='utf-8') == text) for name, text in derived(state).items()}}

    def write(self, path, content, action):
        if path.exists():
            relative = path.relative_to(self.root)
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            backup = self.root / '.workbench' / 'backups' / stamp / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(path.read_bytes())
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.workbench-tmp')
        temporary.write_text(content, encoding='utf-8')
        temporary.replace(path)
        log = self.root / '.workbench' / 'activity.jsonl'
        log.parent.mkdir(parents=True, exist_ok=True)
        entry = {'time': datetime.now().astimezone().isoformat(), 'action': action,
                 'path': path.relative_to(self.root).as_posix()}
        with log.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def save_file(self, body):
        with self.lock:
            path = self.path(body.get('path'))
            content = body.get('content')
            if not isinstance(content, str) or len(content.encode('utf-8')) > MAX_FILE:
                raise ValueError('文件内容必须是 2 MB 以内的文本。')
            if not path.is_file() or digest(path.read_bytes()) != body.get('expected_sha'):
                raise Conflict('文件被 WorkBuddy 或其他窗口改动了。草稿已保留，请读取最新内容后再编辑。')
            if body['path'] in derived(self.state()):
                raise ValueError('这是自动生成的设计文档，请修改结构化设计，避免产生第二份事实来源。')
            if path == self.state_path:
                state = json.loads(content)
                return self.save_state({'state': state, 'expected_revision': self.snapshot()['revision']})
            else:
                state = self.state()
                before = path.read_text(encoding='utf-8-sig')
                self.write(path, content, '网页保存文件')
                business = True
                if path.suffix == '.py':
                    try:
                        business = ast.dump(ast.parse(before)) != ast.dump(ast.parse(content))
                    except SyntaxError:
                        pass
                ids = []
                for module in state['modules']:
                    for artifact in module.get('artifacts', []):
                        if artifact.get('path') == body['path']:
                            anchor = str(artifact.get('content', '')).split('\n')[0]
                            if anchor.startswith('## ') and anchor in before and anchor in content:
                                def section(text):
                                    start = text.index(anchor); end = text.find('\n## ', start + len(anchor))
                                    return text[start:end if end >= 0 else None]
                                if section(before) == section(content): continue
                            ids.append(module['id']); artifact['outdated'] = True
                for node in state['design']['contracts'].get('nodes', {}).values():
                    if node.get('source') == body['path']: ids.append('nodes')
                affect(state, ids, f'{body["path"]} 的' + ('业务内容改变。' if business else '注释或格式改变，请核对讲解。'), business)
                state.setdefault('open_questions', [])
                note = f'需复核：网页修改了 {body["path"]}，请核对相关讲解、结构与代码。'
                if note not in state['open_questions']:
                    state['open_questions'].append(note)
                if state.get('design_status') == '设计完成':
                    state['design_status'] = '需复核'
                self.write(self.state_path, json.dumps(state, ensure_ascii=False, indent=2), '关联内容标记需复核')
            return self.snapshot()

    def save_state(self, body):
        with self.lock:
            if self.snapshot()['revision'] != body.get('expected_revision'):
                raise Conflict('项目有新成果。草稿已保留，请先读取最新内容，避免覆盖 WorkBuddy 的更新。')
            state = body.get('state')
            validate(state)
            requested_complete = state.get('design_status') == '设计完成'
            baseline = self.root / '.workbench' / 'last-design.json'
            previous = json.loads(baseline.read_text(encoding='utf-8')) if baseline.exists() else self.state()
            state = reconcile(state, previous)
            change = change_record(state, previous)
            # History is generated from actual changes, not accepted from arbitrary UI content.
            history = previous.get('design_changes', [])
            state['design_changes'] = (history + ([change] if change and (not history or history[-1]['id'] != change['id']) else []))[-20:]
            validate({**state, 'design_status': '进行中'})
            state['teaching_version'] = VERSION
            outputs = derived(state)
            # Preflight all generated file names before writing any of them.
            for name in outputs:
                path = self.path(name)
                if path.exists():
                    old = path.read_text(encoding='utf-8-sig')
                    if not (old.startswith('<!-- generated by agent-development-coach') or old.startswith('%% generated by agent-development-coach') or ('"generated_by": "agent-development-coach"' in old and name.endswith('.json'))):
                        raise Conflict(name + ' 已有手工内容，先改名保留再同步；不会覆盖。')
            if requested_complete:
                result = audit(state, self.root)
                blocking = [i for i in result['issues'] if '尚未同步' not in i['message']]
                if blocking: raise ValueError('不能标记设计完成：' + '；'.join(i['message'] for i in blocking[:8]))
                state['design_status'] = '设计完成'
            for name, text in outputs.items():
                path = self.path(name)
                if not path.exists() or path.read_text(encoding='utf-8') != text:
                    self.write(path, text, '结构化设计同步生成文档')
            self.write(self.state_path, json.dumps(state, ensure_ascii=False, indent=2), '网页保存设计或架构草稿')
            baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
            return self.snapshot()

    def design_request(self, body):
        with self.lock:
            if self.snapshot()['revision'] != body.get('expected_revision'):raise Conflict('项目有更新，请先读取最新设计再提交需求。')
            text=body.get('text','')
            if not isinstance(text,str) or not 2<=len(text.strip())<=4000:raise ValueError('请写 2–4000 字的设计需求。')
            state=self.state();module=body.get('module',state['current_module'])
            if module not in {m['id'] for m in state['modules']}:raise ValueError('选择一个真实设计结构。')
            if len([r for r in state['design_requests'] if r['status']=='queued'])>=30:raise ValueError('已有 30 条待处理需求，请先让 WorkBuddy 处理。')
            state['design_requests'].append({'id':uuid.uuid4().hex[:16],'text':text.strip(),'module':module,
                'node':body.get('node','') if body.get('node','') in {n['id'] for n in state['agent_graph']['nodes']} else '',
                'status':'queued','time':datetime.now().astimezone().isoformat(),'design_hash':design_change_hash(state['design'])})
            return self.save_state({'state':state,'expected_revision':body['expected_revision']})

    def exercise(self, body):
        with self.lock:
            if self.snapshot()['revision'] != body.get('expected_revision'): raise Conflict('设计已经更新，请读取最新再回答。')
            state = grade(self.state(), body['module'], body.get('answer'), body.get('reason', ''))
            return self.save_state({'state': state, 'expected_revision': body['expected_revision']})

    def run(self, body):
        if body.get('mode') not in ('design', 'framework', 'real'): raise ValueError('请选择三种明确的运行模式。')
        initial = self.snapshot()
        if initial['revision'] != body.get('expected_revision'): raise Conflict('请先保存并读取最新设计，再运行。')
        runner = Path(__file__).with_name('run_design.py')
        command = [sys.executable, '-X', 'utf8', str(runner), '--project', str(self.root), '--mode', body['mode'], '--input-json', json.dumps(body.get('question', ''), ensure_ascii=False)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=65,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            data = json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            raise ValueError('运行超时，已结束本次进程；没有记录为通过。')
        except (ValueError, TypeError, OSError) as e:
            raise ValueError('运行失败：' + str(e))
        with self.lock:
            if self.snapshot()['revision'] != initial['revision']:
                data['stale'] = True
                return {'run_result': data, **self.snapshot()}
            state = self.state()
            state['trace'] = data.get('events', [])
            state.setdefault('runs', []).append({k: v for k, v in data.items() if k != 'events'})
            state['runs'] = state['runs'][-30:]
            state['implementation']['verification'] = f'{data["mode"]}：{data["status"]}；{data.get("error", "")}'
            self.write(self.state_path, json.dumps(state, ensure_ascii=False, indent=2), '记录实际运行或设计模拟证据')
            return {'run_result': data, **self.snapshot()}


def make_server(project, assets, port):
    token = secrets.token_urlsafe(24)
    service_id = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            if args and str(args[1] if len(args) > 1 else '') not in ('200', '304'):
                super().log_message(fmt, *args)

        def json_response(self, data, status=200):
            raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def same_host(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',
                                               f'localhost:{self.server.server_port}'}

        def do_GET(self):
            if not self.same_host():
                return self.json_response({'error': '仅接受本机工作台请求。'}, 403)
            url = urlparse(self.path)
            if url.path == '/api/health':
                return self.json_response(self.server.service_info)
            if url.path == '/api/snapshot':
                try:
                    snapshot = project.snapshot()
                    query = parse_qs(url.query)
                    if query.get('revision', [''])[0] == snapshot['revision']:
                        return self.json_response({'unchanged': True, 'token': token})
                    snapshot['token'] = token
                    return self.json_response(snapshot)
                except (ValueError, OSError) as error:
                    return self.json_response({'error': str(error)}, 400)
            routes = {'/': 'index.html', '/app.js': 'app.js', '/styles.css': 'styles.css'}
            if url.path not in routes:
                return self.json_response({'error': '没有这个页面。'}, 404)
            data = (assets / routes[url.path]).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mimetypes.guess_type(routes[url.path])[0] + '; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            origin = self.headers.get('Origin')
            accepted_origin = {f'http://127.0.0.1:{self.server.server_port}',
                               f'http://localhost:{self.server.server_port}'}
            if not self.same_host() or origin not in accepted_origin or self.headers.get('X-Workbench-Token') != token:
                return self.json_response({'error': '请从本机工作台页面保存。'}, 403)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BODY:
                    raise ValueError('保存内容大小不正确。')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError('保存内容需要 JSON 对象。')
                if self.path == '/api/shutdown':
                    if body.get('service_id') != service_id:
                        return self.json_response({'error': '服务标识不一致。'}, 403)
                    self.json_response({'stopped': True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                if self.path == '/api/file':
                    snapshot = project.save_file(body)
                elif self.path == '/api/state':
                    snapshot = project.save_state(body)
                elif self.path == '/api/exercise':
                    snapshot = project.exercise(body)
                elif self.path == '/api/design-request':
                    snapshot = project.design_request(body)
                elif self.path == '/api/run':
                    snapshot = project.run(body)
                else:
                    return self.json_response({'error': '没有这个保存入口。'}, 404)
                snapshot['token'] = token
                return self.json_response(snapshot)
            except Conflict as error:
                return self.json_response({'error': str(error)}, 409)
            except (ValueError, KeyError, TypeError, OSError) as error:
                return self.json_response({'error': str(error)}, 400)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.service_info = {'service': 'agent-development-coach', 'version': VERSION,
        'service_id': service_id, 'project_path': str(project.root), 'pid': os.getpid(),
        'fingerprint': bundle_fingerprint(), 'url': f'http://127.0.0.1:{server.server_port}'}
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True, help='学员项目目录')
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--open', action='store_true', help='打开浏览器')
    parser.add_argument('--auto-port', action='store_true', help='端口被占用时自动选用空闲端口')
    parser.add_argument('--service-info', type=Path, help='自动启动器的项目内服务记录')
    parser.add_argument('--export', type=Path, help='只导出可离线查看和编辑草稿的独立 HTML')
    args = parser.parse_args()
    assets = Path(__file__).resolve().parents[1] / 'assets' / 'workbench'
    try:
        project = Project(args.project)
        if args.export:
            snapshot = project.snapshot()
            snapshot.pop('project_path', None)
            embedded = json.dumps(snapshot, ensure_ascii=False).replace('<', '\\u003c')
            page = (assets / 'index.html').read_text(encoding='utf-8')
            page = page.replace('<link rel="stylesheet" href="/styles.css">',
                                '<style>' + (assets / 'styles.css').read_text(encoding='utf-8') + '</style>')
            page = page.replace('<script src="/app.js" defer></script>',
                                '<script id="offline-data" type="application/json">' + embedded + '</script><script>'
                                + (assets / 'app.js').read_text(encoding='utf-8').replace('</script', '<\\/script') + '</script>')
            args.export.parent.mkdir(parents=True, exist_ok=True)
            args.export.write_text(page, encoding='utf-8')
            print('独立 HTML 已导出：' + str(args.export.resolve()))
            return
        try:
            server = make_server(project, assets, args.port)
        except OSError as error:
            if args.auto_port and (error.errno in (48, 98, 10048) or getattr(error, 'winerror', None) in (10013, 10048)):
                server = make_server(project, assets, 0)
            else:
                raise
        if args.service_info:
            info_path = args.service_info.resolve()
            if not info_path.is_relative_to(project.root / '.workbench'):
                raise ValueError('服务记录必须保存在项目 .workbench 目录。')
            info_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = info_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(server.service_info, ensure_ascii=False), encoding='utf-8')
            temporary.replace(info_path)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    url = f'http://127.0.0.1:{server.server_port}'
    print('本地智能体教学工作台：' + url, flush=True)
    print('项目：' + str(project.root), flush=True)
    print('保持窗口运行；Ctrl+C 停止。网页保存会写入项目文件并保留备份。', flush=True)
    if args.open:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
