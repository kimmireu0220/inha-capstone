#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
/usr/bin/time -l .venv-local-image/bin/mflux-generate-flux2-edit \
 --model Runpod/FLUX.2-klein-4B-mflux-4bit --base-model flux2-klein-4b \
 --quantize 4 --low-ram \
 --image-paths experiments/trigger-validation-v1/P04/reference.png \
 --prompt-file experiments/local-open-model-v1/prompt.txt \
 --width 512 --height 768 --steps 4 --seed 42 --metadata \
 --output experiments/local-open-model-v1/output.png
