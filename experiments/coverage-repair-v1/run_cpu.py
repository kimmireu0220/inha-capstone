"""CPU fallback for MLX-LM's GPU-only wired-memory context.

The frozen inference algorithm, model weights, prompts and decoding are unchanged.
Both methods run on CPU; timing must not be compared to previous GPU experiments.
"""
import contextlib
import importlib
from pathlib import Path
import runpy

import mlx.core as mx

mx.set_default_device(mx.cpu)
generation = importlib.import_module('mlx_lm.generate')
generation.generation_stream = mx.new_thread_local_stream(mx.cpu)
generation.wired_limit = lambda *args, **kwargs: contextlib.nullcontext()
print('CPU inference; GPU wired-memory context disabled', flush=True)
runpy.run_path(str(Path(__file__).resolve().with_name('run.py')), run_name='__main__')
