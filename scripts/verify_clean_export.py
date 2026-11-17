"""Verify a clean export of the exact public Git index, without private caches."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
git = os.getenv('HOMEVOICE_GIT', 'git')
subprocess.run([sys.executable, '-X', 'utf8', 'scripts/check_public_files.py'], cwd=ROOT, check=True)
tree = subprocess.check_output([git, 'write-tree'], cwd=ROOT, text=True).strip()
cache = ROOT / 'cache/clean-export'
cache.mkdir(parents=True, exist_ok=True)
destination = Path(tempfile.mkdtemp(prefix=tree[:12] + '-', dir=cache)).resolve()
if not destination.is_relative_to(cache.resolve()):
    raise ValueError('Export destination outside benchmark cache')
archive = destination / 'index.zip'
subprocess.run([git, 'archive', '--format=zip', '--output=' + str(archive), tree], cwd=ROOT, check=True)
checkout = destination / 'checkout'
checkout.mkdir()
with zipfile.ZipFile(archive) as bundle:
    if bundle.testzip() is not None:
        raise ValueError('Clean export CRC failure')
    for entry in bundle.infolist():
        target = (checkout / entry.filename).resolve()
        if not target.is_relative_to(checkout.resolve()):
            raise ValueError('Invalid archive member path')
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(entry))
manifest = json.loads((checkout / 'data/manifest.json').read_text('utf-8'))
if len(manifest['cases']) != 1000:
    raise ValueError('Expected all 1000 frozen cases')
for entry in manifest['cases']:
    source = (checkout / entry['path']).resolve()
    if not source.is_relative_to(checkout.resolve()):
        raise ValueError('Invalid frozen case path')
    if hashlib.sha256(source.read_bytes()).hexdigest() != entry['file_sha256']:
        raise ValueError('Frozen case changed in clean export: ' + entry['path'])
syntax = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'compileall', '-q', 'homevoice', 'scripts'], cwd=checkout, capture_output=True, text=True, encoding='utf-8')
tests = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=checkout, capture_output=True, text=True, encoding='utf-8')
report = {'git_tree': tree, 'source': 'clean Git index export', 'frozen_cases_verified': len(manifest['cases']), 'syntax_exit_code': syntax.returncode, 'tests_exit_code': tests.returncode, 'test_output': tests.stdout + tests.stderr, 'syntax_output': syntax.stdout + syntax.stderr, 'status': 'passed' if not syntax.returncode and not tests.returncode else 'failed'}
(ROOT / 'reports/clean_export_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
print(json.dumps({k: v for k, v in report.items() if not k.endswith('_output')}))
if report['status'] != 'passed':
    raise SystemExit(1)
