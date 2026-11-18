import argparse,concurrent.futures,json,sys,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.runner import execute,ROOT
ap=argparse.ArgumentParser();ap.add_argument('--system',choices=['qwen35_2b','qwen35_4b','edge_native'],required=True);ap.add_argument('--urls',required=True);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--limit',type=int,default=0);ap.add_argument('--cases');ap.add_argument('--ready-only',action='store_true');ap.add_argument('--probe-label');args=ap.parse_args()
urls=args.urls.split(',');paths=sorted((ROOT/'data/cases').glob('*.json'));lock=threading.Lock();done=0
if args.cases:paths=[p for p in paths if p.stem in args.cases.split(',')]
if args.ready_only:paths=[p for p in paths if json.loads(p.read_text('utf-8'))['variants'][0]['status']=='ready']
if args.limit:paths=paths[:args.limit]
out=ROOT/'runs'/args.system if not args.probe_label else ROOT/'runs/performance'/args.probe_label/args.system;out.mkdir(parents=True,exist_ok=True)
def work(item):
    global done
    index,p=item;target=out/p.name
    if target.exists():return
    case=json.loads(p.read_text('utf-8'));r=execute(case,args.system,urls[index%len(urls)]);temp=target.with_suffix('.tmp');temp.write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf-8');temp.replace(target)
    with lock:
        done+=1
        if done%10==0:print(json.dumps({'system':args.system,'done':done,'case':p.stem,'status':r['execution']['status']}),flush=True)
if args.system=='edge_native' and len(urls)>1:
    # One case at a time per independent worker, including tool loops and talker state.
    def partition(worker):
        for i,p in enumerate(paths):
            if i%len(urls)==worker:work((i,p))
    with concurrent.futures.ThreadPoolExecutor(len(urls)) as pool:list(pool.map(partition,range(len(urls))))
else:
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:list(pool.map(work,enumerate(paths)))
print(json.dumps({'system':args.system,'new_runs':done,'total_files':len(list(out.glob('*.json')))}),flush=True)
