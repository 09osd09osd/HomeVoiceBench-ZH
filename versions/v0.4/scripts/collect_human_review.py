"""Import an actual reviewer export for analysis; never rewrite run results."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT
from homevoice.human_review import collect,read

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);args=parser.parse_args()
    result=collect(read(args.input),ROOT);result['source_export']=str(args.input.resolve())
    folder=ROOT/'reports/human_calibration';folder.mkdir(parents=True,exist_ok=True)
    import hashlib
    digest=hashlib.sha256(args.input.read_bytes()).hexdigest();out=folder/(digest+'.json')
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({k:result[k] for k in ['status','required_records','required_cases','resolved_records']},ensure_ascii=False))
    print(str(out));raise SystemExit(0 if result['status']=='ready_for_calibration_analysis' else 1)
