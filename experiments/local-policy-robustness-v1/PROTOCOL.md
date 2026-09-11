# Post-hoc ROI and registration sensitivity — 2026-09-10

This additional analysis was designed after seeing local-policy-v1's fixed-face comparison; it is not preregistered and does not add images or evaluators. Preserve the original result. Use all8 saved outputs, report final4 separately, no filtering or best-setting selection.

Input512×768; face[176,44,336,224]. Skin regions are exact half-size coordinates of the pre-existing P04 forehead/left/right-cheek regions. NCC translation search ±32px; Gaussian sigma0.5/1.5/3 equals half of the high-resolution1/3/6 settings. These settings are sensitivity checks, not thresholds. Record boundary and shift spread. Highpass is gray minus Gaussian sigma1. All positions are integer crop only; image arrays are not warped.

For each region compute raw RGB MAE, SSIM, highpass MAE, and mean-RGB-removed residual MAE. Decompose MSE into squared mean offset and residual MSE; these MSE components add exactly up to numerical error. Do not describe mean offset as causal lighting effect, nor residual as true degradation. Aggregate by pixel counts, except SSIM weighted by valid7×7 window counts. MAE components are not additive. No LPIPS on tiny skin patches.

Verify input/output hashes, exact reference control, known synthetic translation recovery, MSE decomposition, and fixed face values against original results. Synthetic translated array is a computational check, not a new generated image. No p-values or population intervals from two seeds.
