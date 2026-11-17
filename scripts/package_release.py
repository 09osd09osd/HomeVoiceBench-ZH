"""Build bounded, resumable release ZIPs; no model weights or credentials."""
import argparse,hashlib,json,zipfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from homevoice.cloud import load_key
secrets=[]
for provider in ['bailian','deepseek']:
    try:secrets.append(load_key(provider).encode())
    except Exception:pass
def read(p):return json.loads(p.read_text('utf-8'))
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--part',choices=['inputs','evaluation'],required=True);ap.add_argument('--max-mib',type=int,default=450);args=ap.parse_args()
if args.part=='inputs':
    manifest=read(ROOT/'data/manifest.json');files=[ROOT/a['path'] for a in manifest['audio']]
else:
    audit=read(ROOT/'reports/release_audit.json')
    if audit['status']!='passed' or audit['scope']!='complete_release':raise ValueError('Complete audited evaluation required before packaging')
    files=list((ROOT/'runs').rglob('*.json'))
    referenced={t['assistant_audio']['path'] for system in ['edge_native','qwen35_2b','qwen35_4b'] for p in (ROOT/'runs'/system).glob('*.json') for t in read(p)['turns'] if t.get('assistant_audio')}
    files.extend(ROOT/p for p in referenced)
    # Include available historical/probe output waves with their cache records,
    # so unpacking the release does not leave those cached paths dangling.
    for kind in ['edge_audio','tts']:
        for p in (ROOT/'runs'/kind).glob('*.json'):
            meta=read(p);wave=ROOT/meta['path']
            if wave.is_file():files.append(wave)
files=sorted(set(files));out=ROOT/'release_parts';out.mkdir(exist_ok=True);groups=[];current=[];size=0;limit=args.max_mib*1024**2
for p in files:
    resolved=p.resolve()
    if not resolved.is_relative_to(ROOT.resolve()) or not p.is_file():raise ValueError('Invalid archive source')
    if p.suffix=='.json' and any(key and key in p.read_bytes() for key in secrets):raise ValueError('Configured credential found in archive source: '+p.relative_to(ROOT).as_posix())
    if current and size+p.stat().st_size>limit:groups.append(current);current=[];size=0
    current.append(p);size+=p.stat().st_size
if current:groups.append(current)
records=[]
for i,group in enumerate(groups,1):
    name=f'homevoicebench-zh-v0.2-{args.part}-{i:03d}.zip';target=out/name;index=out/(name+'.manifest.json')
    members=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in group]
    source_hash=hashlib.sha256(json.dumps(members,sort_keys=True).encode()).hexdigest()
    old=read(index) if index.exists() else None
    if not old or old.get('source_sha256')!=source_hash or not target.exists() or digest(target)!=old['sha256']:
        temp=target.with_suffix('.tmp')
        with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
            for p in group:z.write(p,p.relative_to(ROOT).as_posix())
            z.writestr('release_manifest_'+args.part+f'_{i:03d}.json',json.dumps({'source_sha256':source_hash,'files':members},ensure_ascii=False,indent=2))
        temp.replace(target);old={'name':name,'path':target.relative_to(ROOT).as_posix(),'bytes':target.stat().st_size,'sha256':digest(target),'source_sha256':source_hash,'files':len(members),'uncompressed_bytes':sum(x['bytes'] for x in members)}
        index.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n','utf-8')
    with zipfile.ZipFile(target) as z:
        bad=z.testzip()
        if bad is not None:raise ValueError('Archive CRC failure: '+bad)
    old['archive_crc_verified']=True;index.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n','utf-8')
    records.append(old);print(json.dumps(old),flush=True)
report=ROOT/'reports/release_assets.json';all_records=read(report) if report.exists() else {};all_records[args.part]=records;report.write_text(json.dumps(all_records,ensure_ascii=False,indent=2)+'\n','utf-8')
