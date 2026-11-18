"""Bounded evidence archives extracted at repository root; never model weights/keys."""
import argparse,concurrent.futures,hashlib,json,re,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import CODE_ROOT as CODE,SHARED_ROOT
from homevoice.cloud import load_key

def read(p):return json.loads(p.read_text('utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--part',choices=['inputs','evaluation','history'],required=True);ap.add_argument('--max-mib',type=int,default=450);a=ap.parse_args()
    files=[]
    for split in ['pilot','benchmark']:
        root=CODE/split
        if a.part=='inputs':
            manifest=read(root/'data/manifest.json')
            for entry in manifest['cases']:
                if sha(root/entry['path'])!=entry['sha256']:raise ValueError('Frozen input changed')
                case=read(root/entry['path'])
                for meta in case['variants'][0]['audio_assets']:
                    wave=root/meta['path']
                    if sha(wave)!=meta['sha256']:raise ValueError('Referenced input audio changed')
                    files.append(wave)
        if a.part=='evaluation':
            if read(root/'reports/acceptance.json')['status']!='passed':raise ValueError('Complete audited results required')
            files+=list((root/'runs').rglob('*.json'))
            files+=list((root/'assets/audio/edge').glob('*.wav'))+list((root/'assets/audio/baseline').glob('*.wav'))
    if a.part=='history':
        for history in ['initial_protocol','pre_full_run_protocol']:
            root=CODE/'pilot_history'/history
            files += [p for p in root.rglob('*') if p.is_file() and not set(p.relative_to(root).parts)&{'cache','logs','outputs','runtime','__pycache__','human_calibration'} and p.suffix in {'.json','.jsonl','.wav','.md','.html','.css','.js'}]
    keys=[load_key(s).encode() for s in ['bailian','deepseek']];files=sorted(set(files));groups=[];group=[];size=0
    for p in files:
        if not p.resolve().is_relative_to(CODE.resolve()):raise ValueError('Archive path outside v0.4')
        if p.suffix in {'.json','.jsonl'} and (any(k in p.read_bytes() for k in keys) or re.search(rb'\bsk-[A-Za-z0-9]{24,}\b|sk-ws-[A-Za-z0-9._-]{25,}',p.read_bytes())):raise ValueError('Credential found in archive source: '+p.relative_to(CODE).as_posix())
        if group and size+p.stat().st_size>a.max_mib*1024**2:groups.append(group);group=[];size=0
        group.append(p);size+=p.stat().st_size
    if group:groups.append(group)
    out=CODE/'release_parts';out.mkdir(exist_ok=True)
    def build(item):
        i,group=item;name=f'homevoicebench-zh-v0.4-{a.part}-{i:03d}.zip';target=out/name;index=out/(name+'.manifest.json')
        members=[{'path':p.relative_to(SHARED_ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in group]
        source_sha=hashlib.sha256(json.dumps(members,sort_keys=True).encode()).hexdigest();old=read(index) if index.exists() else None
        if not old or old['source_sha256']!=source_sha or not target.exists() or sha(target)!=old['sha256']:
            temp=target.with_suffix('.tmp')
            with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
                for p in group:z.write(p,p.relative_to(SHARED_ROOT).as_posix())
                z.writestr(f'versions/v0.4/release_manifest_{a.part}_{i:03d}.json',json.dumps({'files':members,'source_sha256':source_sha},ensure_ascii=False,indent=2))
            temp.replace(target);old={'name':name,'path':target.relative_to(CODE).as_posix(),'bytes':target.stat().st_size,'sha256':sha(target),'source_sha256':source_sha,'files':len(members),'uncompressed_bytes':sum(x['bytes'] for x in members)}
        with zipfile.ZipFile(target) as z:
            if z.testzip() is not None:raise ValueError('ZIP CRC failure')
        old['archive_crc_verified']=True;index.write_text(json.dumps(old,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(old),flush=True);return old
    with concurrent.futures.ThreadPoolExecutor(3) as pool:records=list(pool.map(build,enumerate(groups,1)))
    report=CODE/'reports'/f'release_assets_{a.part}.json';report.parent.mkdir(exist_ok=True);report.write_text(json.dumps(records,ensure_ascii=False,indent=2),'utf-8')
