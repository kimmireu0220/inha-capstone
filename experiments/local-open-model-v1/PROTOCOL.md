# Local open model feasibility test

2026-09-09. Apple M1, 16 GiB unified memory, Metal supported. Separate Python environment .venv-local-image; existing research environment unchanged.

Test FLUX.2 Klein 4B distilled, 4-bit quantized, via MFLUX on Apple GPU. Qwen-Image-Edit-2509 was initially considered but is much larger. This is a platform feasibility smoke test, not a replication of the earlier generator's research results.

Use existing synthetic P04 reference. Request navy shirt, pale blue background and one silver pin, preserving face/pose. First output retained, seed42, four steps, 512x768 output. Record actual runtime and peak memory; visually inspect output. No paid API or cloud compute. Model downloads cached outside Git. Do not interpret a single result as preservation success rate.

Sources:
- https://huggingface.co/black-forest-labs/FLUX.2-klein-4B
- https://github.com/mflux-community/mflux/blob/main/src/mflux/models/flux2/README.md
- https://huggingface.co/Runpod/FLUX.2-klein-4B-mflux-4bit
