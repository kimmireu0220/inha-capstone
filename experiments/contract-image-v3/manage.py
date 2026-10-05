"""Use the preserved native-output recorder with an additional wrapper freeze."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'keep-image-v1/manage.py'
spec = importlib.util.spec_from_file_location('native_contract_image_recorder', SOURCE)
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)
manager.ROOT = ROOT


def main():
    reuse = json.loads((ROOT / 'reuse-plan.json').read_text())
    # This frozen S study has no exact matching P inputs. Do not silently
    # implement a different reuse policy if a future study changes that fact.
    assert reuse['reused_jobs'] == 0 and reuse['new_jobs'] == 66
    plan = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ['manage.py', 'reuse-plan.json', 'prepare_reuse.py']}
    path = ROOT / 'wrapper-plan.json'
    if path.exists():
        assert json.loads(path.read_text()) == plan
    else:
        manager.save(path, plan)
    manager.main()


if __name__ == '__main__':
    main()
