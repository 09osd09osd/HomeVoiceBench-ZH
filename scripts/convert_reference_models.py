"""Use the pinned upstream converter on the existing original HF checkpoints."""
import hashlib,json,shutil,subprocess,sys,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];source=ROOT/'runtime/llama-b11552-source';archive=ROOT/'cache/llama-b11552-source.zip'
sys.path.insert(0,str(ROOT))
from homevoice.paths import model_path
if not (source/'PINNED_SOURCE.json').exists() and not archive.exists():
    req=urllib.request.Request('https://codeload.github.com/ggml-org/llama.cpp/zip/refs/tags/b11552',headers={'User-Agent':'HomeVoiceBench-ZH'})
    with urllib.request.urlopen(req,timeout=120) as r,archive.with_suffix('.part').open('wb') as f:shutil.copyfileobj(r,f)
    archive.with_suffix('.part').replace(archive)
if not (source/'PINNED_SOURCE.json').exists() and not (source/'convert_hf_to_gguf.py').exists():
    source.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            parts=Path(entry.filename).parts[1:]
            if not parts or entry.is_dir():continue
            target=source.joinpath(*parts)
            if not target.resolve().is_relative_to(source.resolve()):raise ValueError('unsafe archive path')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(entry))
source_manifest=source/'PINNED_SOURCE.json' if (source/'PINNED_SOURCE.json').exists() else archive
source_hash=hashlib.file_digest(source_manifest.open('rb'),'sha256').hexdigest()
print(json.dumps({'source_ready':True,'source_manifest_sha256':source_hash}),flush=True)
records=[]
for size,hf in [('2B',model_path('source_2b')),('4B',model_path('source_4b'))]:
    intermediate=ROOT/'models'/f'Qwen3.5-{size}-b11552-BF16.gguf';output=ROOT/'models'/f'Qwen3.5-{size}-Q8_0.gguf';marker=ROOT/'reports'/f'conversion_{size}.json'
    if marker.exists() and output.exists():continue
    if output.exists():
        target=ROOT/'cache'/f'incompatible_newer_converter-{size}-Q8_0.gguf'
        if target.exists():raise ValueError('inspect existing conversion archive')
        if not output.resolve().is_relative_to(ROOT.resolve()) or not target.resolve().is_relative_to(ROOT.resolve()):raise ValueError('path outside project')
        output.replace(target)
    if not intermediate.exists():
        with (ROOT/'logs'/f'convert-{size}.log').open('w',encoding='utf-8') as log:
            subprocess.run([sys.executable,'-X','utf8',str(source/'convert_hf_to_gguf.py'),str(hf),'--outfile',str(intermediate),'--outtype','bf16'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    with (ROOT/'logs'/f'quantize-{size}-compatible.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(ROOT/'runtime/llama-b11552/llama-quantize.exe'),intermediate.relative_to(ROOT).as_posix(),output.relative_to(ROOT).as_posix(),'Q8_0','8'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    record={'size':size,'source':'original local official HF checkpoint','converter':'llama.cpp b11552','source_manifest_sha256':source_hash,'gguf_sha256':hashlib.file_digest(output.open('rb'),'sha256').hexdigest(),'quantization':'Q8_0','reason':'Existing GGUF came from a newer tensor-layout converter; reconvert original weights with the reference runtime version.'}
    marker.write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(record),flush=True)
