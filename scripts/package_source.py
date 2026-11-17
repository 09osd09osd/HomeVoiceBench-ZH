"""Export the audited Git index without requiring an identity or remote login."""
import hashlib,json,os,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
git=os.getenv('HOMEVOICE_GIT','git')
def read(p):return json.loads(p.read_text('utf-8'))
if read(ROOT/'reports/summary.json')['evaluation_status']!='complete':raise ValueError('Complete evaluation required')
subprocess.run([os.sys.executable,'-X','utf8','scripts/check_public_files.py'],cwd=ROOT,check=True)
tree=subprocess.check_output([git,'write-tree'],cwd=ROOT,text=True).strip()
out=ROOT/'release_parts/homevoicebench-zh-v0.2-source.zip'
out.parent.mkdir(exist_ok=True)
subprocess.run([git,'archive','--format=zip','--output='+str(out),tree],cwd=ROOT,check=True)
with zipfile.ZipFile(out) as z:
    if z.testzip() is not None:raise ValueError('Source ZIP CRC failure')
    count=len([x for x in z.infolist() if not x.is_dir()])
with out.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
record={'name':out.name,'path':out.relative_to(ROOT).as_posix(),'bytes':out.stat().st_size,'sha256':digest,'git_tree':tree,'files':count,'archive_crc_verified':True,'contents':'audited index: code, frozen text cases, specifications, reports, Excel and HTML; separate input/evaluation archives contain full WAV and run evidence'}
(ROOT/'reports/source_archive.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(record))
