#!/usr/bin/env python3
"""Skill entry point: initialize, ensure, reuse and open a local workbench."""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from workbench import Project, VERSION, bundle_fingerprint

SKILL = Path(__file__).resolve().parents[1]


def local_url(value):
    parsed = urlparse(value)
    return parsed.scheme == 'http' and parsed.hostname == '127.0.0.1' and parsed.port and not parsed.username and not parsed.password and parsed.path in ('', '/') and not parsed.query and not parsed.fragment


def request_json(url, data=None, token=None):
    headers = {'Origin': url.split('/api/')[0]}
    if token:
        headers['X-Workbench-Token'] = token
    request = urllib.request.Request(url, json.dumps(data).encode() if data is not None else None, headers=headers)
    with urllib.request.urlopen(request, timeout=1) as response:
        return json.loads(response.read())


def running(info_path, root):
    try:
        info = json.loads(info_path.read_text(encoding='utf-8'))
        if not local_url(info['url']):
            return None
        health = request_json(info['url'] + '/api/health')
        if health.get('service') == 'agent-development-coach' and health.get('service_id') == info.get('service_id') and Path(health['project_path']).resolve() == root:
            return {**health, 'url': info['url']}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def initialize(root, demo=False):
    state_path = root / 'agent-design' / 'teaching-state.json'
    if not state_path.resolve().is_relative_to(root):
        raise ValueError('教学进度必须保存在当前项目内。')
    if state_path.exists():
        Project(root)
        return False
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if demo:
        example = SKILL / 'templates' / 'course-example'
        sources = [p for p in example.rglob('*') if p.is_file()]
        if any((root / p.relative_to(example)).exists() for p in sources):
            raise ValueError('示例文件名与已有项目重合，请在新的示例目录启动；不会覆盖已有文件。')
        for source in sources:
            target = root / source.relative_to(example)
            if not target.resolve().is_relative_to(root):
                raise ValueError('示例文件必须保存在当前项目内。')
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(source.read_bytes())
    template = SKILL / 'templates' / ('example-state.json' if demo else 'teaching-state.json')
    state = json.loads(template.read_text(encoding='utf-8'))
    state['teaching_version'] = VERSION
    with state_path.open('x', encoding='utf-8') as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
    Project(root)
    return True


def ensure(root, port=8766, demo=False, open_browser=True, stop=False, timeout=12):
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    runtime = root / '.workbench'
    if not runtime.resolve().is_relative_to(root):
        raise ValueError('工作台记录目录须在当前项目内。')
    runtime.mkdir(exist_ok=True)
    info_path = runtime / 'service.json'
    lock_path = runtime / 'launch.lock'
    deadline = time.monotonic() + timeout
    while True:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(descriptor)
            break
        except FileExistsError:
            if time.time() - lock_path.stat().st_mtime > 60:
                lock_path.unlink(missing_ok=True)
                continue
            if time.monotonic() > deadline:
                raise ValueError('另一个启动正在进行，请稍后重试。')
            time.sleep(0.1)
    try:
        existing = running(info_path, root)
        if stop:
            if existing:
                token = request_json(existing['url'] + '/api/snapshot')['token']
                request_json(existing['url'] + '/api/shutdown', {'service_id': existing['service_id']}, token)
                while running(info_path, root) and time.monotonic() < deadline:
                    time.sleep(0.1)
                info_path.unlink(missing_ok=True)
                time.sleep(0.15)
            return {'status': 'stopped' if existing else 'not-running', 'project_path': str(root)}
        initialized = initialize(root, demo)
        fingerprint = bundle_fingerprint()
        if existing and existing.get('version') == VERSION and existing.get('fingerprint') == fingerprint:
            result = {**existing, 'status': 'reused', 'initialized': initialized}
        else:
            log_path = runtime / 'service.log'
            args = [sys.executable, '-X', 'utf8', '-u', str(SKILL / 'scripts' / 'workbench.py'),
                    '--project', str(root), '--port', str(port), '--auto-port', '--service-info', str(info_path)]
            options = {'stdin': subprocess.DEVNULL, 'close_fds': True, 'cwd': str(root)}
            if os.name == 'nt':
                options['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                options['start_new_session'] = True
            with log_path.open('ab') as log:
                child = subprocess.Popen(args, stdout=log, stderr=log, **options)
            while time.monotonic() < deadline:
                latest = running(info_path, root)
                if latest and latest['pid'] == child.pid and latest.get('fingerprint') == fingerprint:
                    result = {**latest, 'status': 'started', 'initialized': initialized}
                    break
                if child.poll() is not None:
                    raise ValueError('后台服务启动失败，请读取项目 .workbench/service.log。')
                time.sleep(0.15)
            else:
                # Stop only the process started by this invocation, never an unrelated PID.
                child.terminate()
                raise ValueError('后台服务未在时限内就绪，请读取项目 .workbench/service.log。')
        result.pop('service_id', None)
        result.pop('fingerprint', None)
        result['browser_open_requested'] = bool(open_browser)
        if open_browser:
            result['browser_open_accepted'] = bool(webbrowser.open(result['url']))
        return result
    finally:
        lock_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--demo', action='store_true', help='在新目录初始化课堂模拟案例')
    parser.add_argument('--no-open', action='store_true', help='由宿主浏览器工具打开返回 URL')
    parser.add_argument('--stop', action='store_true', help='仅停止本项目登记且核验通过的工作台')
    args = parser.parse_args()
    try:
        result = ensure(args.project, args.port, args.demo, not args.no_open, args.stop)
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError) as error:
        print(json.dumps({'status': 'error', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
