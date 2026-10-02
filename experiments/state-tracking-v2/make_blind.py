"""Prepare masked image pairs using the shared plate generator."""
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('shared_blind', ROOT.parent / 'state-tracking-v1/make_blind.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if __name__ == '__main__':
    module.main(ROOT)
