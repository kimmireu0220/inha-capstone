# Local FLUX batch versus sequential pilot

2026-09-09. Freeze before generation. One synthetic identity P04, seeds42 and314, two arms: batch1 call, sequential3 calls (shirt, background, pin). Eight new outputs; do not reuse the earlier feasibility output. Same cumulative requirements at final stage, same seed within each path, 4bit FLUX.2 Klein4B, MFLUX0.19.1, four denoising steps, low-RAM, 512×768. Alternate arm execution order between seeds. No best-of selection or quality retry.

Resize original1024×1536 once to512×768 with Pillow Lanczos before either arm, so every input and output has the same dimensions. Original remains unchanged. This preprocessing is explicit and this run is not pooled with previous high-resolution experiments.

Each stage uses immediately previous output for sequential; batch uses original reference. Record input/output hashes, exact prompts, seed, exit status, elapsed process time, metadata. Failures remain missing; no silent replacement. Fixed face ROI [176,44,336,224] (half of established P04 ROI). MAE/SSIM/LPIPS versus resized reference, CPU frozen metric implementation. No alignment or threshold fitting. Report each repetition and means; one identity/two seeds is not population inference. Same seeds do not guarantee matched latent trajectories between arms.

Visually inspect all final images for navy shirt, pale blue background, silver pin/viewer-right, and unintended changes. Execution-session observations only, no independent AI/human grades. Record total path time separately from final-call time. Existing human responses do not apply to these images.
