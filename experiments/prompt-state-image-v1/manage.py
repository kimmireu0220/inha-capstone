"""Use existing first-output recorder with this study's frozen input packet."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prompt_image_manager',ROOT.parent/'keep-image-v1/manage.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=ROOT
if __name__=='__main__':m.main()
