"""Reuse the frozen pilot implementation unchanged on a separate dialogue set."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'coverage-repair-v1'
REPO = ROOT.parents[1]


def main():
    files = [Path(__file__), ROOT / 'benchmark.json', ROOT / 'PROTOCOL.md',
             SOURCE / 'run.py', SOURCE / 'ablation.py', REPO / 'local-studio/request_state.py']
    hashes = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    frozen = ROOT / 'method-freeze.json'
    if frozen.exists():
        assert json.loads(frozen.read_text()) == hashes, 'Validation method changed'
    else:
        frozen.write_text(json.dumps(hashes, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('frozen_coverage_runner', SOURCE / 'run.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.ROOT = ROOT
    runner.main()
    spec = importlib.util.spec_from_file_location('frozen_noop_ablation', SOURCE / 'ablation.py')
    ablation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ablation)
    ablation.ROOT = ROOT
    ablation.main()


if __name__ == '__main__':
    main()
