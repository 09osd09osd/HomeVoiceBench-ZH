"""Portable model locations; workstation-specific paths stay in ignored .local/."""
import json,os,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULTS={'edge_model':'models/EdgeInstant-Omni-2B-1106-Preview','tts_model':'models/Qwen3-TTS-12Hz-0.6B-CustomVoice','asr_model':'models/Qwen3-ASR-0.6B','source_2b':'models/Qwen3.5-2B','source_4b':'models/Qwen3.5-4B','ffmpeg':'runtime/ffmpeg/ffmpeg.exe'}
DEFAULTS.update({name+'_python':f'.venv-{name}/'+('Scripts/python.exe' if os.name=='nt' else 'bin/python') for name in ['edge','asr','tts']})
DEFAULTS['cuda_library_dir']='runtime/cuda'
def model_path(name):
    local=ROOT/'.local/runtime.json';settings=json.loads(local.read_text('utf-8')) if local.exists() else {}
    value=os.getenv('HOMEVOICE_'+name.upper()) or settings.get(name) or DEFAULTS[name]
    if name=='ffmpeg' and not (ROOT/value).exists() and shutil.which(value):return Path(shutil.which(value))
    p=Path(value);return p if p.is_absolute() else ROOT/p
