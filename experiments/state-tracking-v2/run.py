"""Run the shared generator against this experiment's frozen inputs."""
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('shared_run', ROOT.parent / 'state-tracking-v1/run.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if __name__ == '__main__':
    module.main(ROOT)
