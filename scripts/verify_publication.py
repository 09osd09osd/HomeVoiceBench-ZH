"""Check the real public release, Pages deployment and served delivery bytes."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT / path).read_text('utf-8'))

publication = read('reports/publication.json')
if publication.get('status') != 'published':
    raise ValueError('Wait for the upload pipeline to finish')
git = os.getenv('HOMEVOICE_GIT', 'git')
env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'Never'}
credential_result = subprocess.run([git, 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n', capture_output=True, text=True, env=env, cwd=ROOT)
credential_values = dict(line.split('=', 1) for line in credential_result.stdout.splitlines() if '=' in line)
token = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN') or credential_values.get('password')
if not token:
    raise ValueError('Existing GitHub authentication required for deployment checks')

def fetch(url, authenticated=False):
    if authenticated and not url.startswith('https://api.github.com/'):
        raise ValueError('Credentials may only be sent to the GitHub API')
    headers = {'User-Agent': 'HomeVoiceBench-ZH-verification'}
    if authenticated:
        headers.update(Authorization='Bearer ' + token, Accept='application/vnd.github+json', **{'X-GitHub-Api-Version': '2022-11-28'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
                return response.status, response.url, response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))

def api(route):
    return json.loads(fetch('https://api.github.com' + route, True)[2])

repo_path = '/repos/' + publication['repository_full_name']
repo = api(repo_path)
local_commit = subprocess.check_output([git, 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
remote_commit = api(repo_path + '/git/ref/heads/main')['object']['sha']
if repo['private'] or repo['default_branch'] != 'main' or remote_commit != local_commit:
    raise ValueError('Public visibility or pushed commit mismatch')
release = api(repo_path + '/releases/tags/v0.3.0')
if release['draft'] or release['prerelease']:
    raise ValueError('Release is not publicly published')
actual_assets = {x['name']: x for x in api(repo_path + '/releases/' + str(release['id']) + '/assets?per_page=100')}
assets = read('reports/release_assets.json')
expected = assets['inputs'] + assets['evaluation'] + [read('reports/source_archive.json')]
for name in ['SHA256SUMS.txt', 'README.md']:
    p = ROOT / 'release_parts' / name
    expected.append({'name': name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
if set(actual_assets) != {x['name'] for x in expected}:
    raise ValueError('Release asset set mismatch')
for entry in expected:
    item = actual_assets[entry['name']]
    if item['state'] != 'uploaded' or item['size'] != entry['bytes'] or item.get('digest') != 'sha256:' + entry['sha256']:
        raise ValueError('Release checksum mismatch: ' + entry['name'])

deadline = time.monotonic() + 300
while True:
    pages = api(repo_path + '/pages')
    build = api(repo_path + '/pages/builds/latest')
    if build.get('status') == 'built' and build.get('commit') == local_commit:
        break
    if time.monotonic() > deadline:
        raise TimeoutError('Latest Pages deployment has not finished')
    print(json.dumps({'waiting_pages': build.get('status'), 'expected_commit': local_commit, 'build_commit': build.get('commit')}), flush=True)
    time.sleep(10)

site = pages['html_url'].rstrip('/') + '/'
run = read('runs/qwen35_4b/T06_003.json')
audio_path = Path(run['turns'][0]['assistant_audio']['path'])
audio_copy = 'docs/audio/' + audio_path.parent.name + '-' + audio_path.name
targets = ['docs/index.html', 'outputs/homevoicebench-v030-20261117/HomeVoiceBench-ZH.xlsx', 'data/cases/T06_003.json', audio_copy]
def check_file(relative):
    status, address, content = fetch(site + relative)
    local = (ROOT / relative).read_bytes()
    if relative.endswith('.html'):
        matching = content.replace(b'\r\n', b'\n') == local.replace(b'\r\n', b'\n')
    else:
        matching = content == local
    if status != 200 or not matching:
        raise ValueError('Public served bytes mismatch: ' + relative)
    return {'path': relative, 'url': address, 'status': status, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(), 'matches_local': True}
with ThreadPoolExecutor(max_workers=3) as pool:
    http_checks = list(pool.map(check_file, targets))
for name in ['SHA256SUMS.txt', 'README.md']:
    status, address, content = fetch(actual_assets[name]['browser_download_url'])
    if status != 200 or content != (ROOT / 'release_parts' / name).read_bytes():
        raise ValueError('Public release download mismatch: ' + name)
    http_checks.append({'path': 'release/' + name, 'status': status, 'bytes': len(content), 'matches_local': True})

report = {'status': 'passed', 'verified_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'repository_url': repo['html_url'], 'visibility': 'public', 'verified_code_commit': local_commit, 'release_url': release['html_url'], 'release_assets': len(expected), 'release_bytes': sum(x['bytes'] for x in expected), 'all_server_sha256_match': True, 'pages_url': site, 'pages_build': {'status': build['status'], 'commit': build['commit']}, 'public_http_checks': http_checks, 'browser_note': 'This report verifies public HTTP bytes and deployment metadata. Browser interaction checks are reported separately.'}
(ROOT / 'reports/publication_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
print(json.dumps({k: report[k] for k in ['status', 'visibility', 'release_assets', 'all_server_sha256_match', 'pages_url']}), flush=True)
