"""Released specifications are canonical; never overwrite frozen schemas."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ['types.schema.json','case.schema.json','run.schema.json','sandbox.json','taxonomy.json','evaluation_profiles.json']:
    json.loads((ROOT/'spec'/name).read_text('utf-8'))
print('Versioned specifications are present. No files were changed.')
