import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from scripts.judge_runs import save

class AtomicJudgeSaveTests(unittest.TestCase):
    def test_windows_reader_lock_retries_without_truncating_previous_result(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'result.json';target.write_text('{"previous":true}','utf-8')
            actual_replace=Path.replace;attempts=[]
            def intermittently_locked(source,destination):
                attempts.append(source)
                self.assertEqual(json.loads(target.read_text('utf-8')),{'previous':True})
                if len(attempts)<3:raise PermissionError('simulated Windows reader lock')
                return actual_replace(source,destination)
            with patch.object(Path,'replace',intermittently_locked),patch('scripts.judge_runs.time.sleep'):
                save(target,{'complete':True,'score':4})
            self.assertEqual(len(attempts),3)
            self.assertEqual(json.loads(target.read_text('utf-8')),{'complete':True,'score':4})
            self.assertEqual(list(Path(folder).glob('*.tmp')),[])

if __name__=='__main__':unittest.main()
