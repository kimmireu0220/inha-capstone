"""Measure original-to-output identity similarity with InsightFace buffalo_l.

The six reference images and the 36 final outputs already produced by this
experiment are analysed. No image generation or score thresholding occurs.
"""
from __future__ import annotations

import csv
import hashlib
import json
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis


ROOT = Path(__file__).resolve().parent
MODEL_ROOT = Path.home() / ".insightface"
PEOPLE = [f"P{i:02d}" for i in range(1, 7)]
SEEDS = [42, 314, 2026]
MODES = ["regenerate", "sequential"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_single_face(app: FaceAnalysis, path: Path):
    image = cv2.imread(str(path))
    if image is None:
        raise RuntimeError(f"Cannot read image: {path}")
    faces = app.get(image)
    if len(faces) != 1:
        raise RuntimeError(f"Expected one face, found {len(faces)}: {path}")
    face = faces[0]
    return face.normed_embedding.astype(np.float64), {
        "bbox": [float(x) for x in face.bbox],
        "det_score": float(face.det_score),
    }


def main() -> None:
    app = FaceAnalysis(
        name="buffalo_l",
        root=str(MODEL_ROOT),
        allowed_modules=["detection", "recognition"],
        providers=["CPUExecutionProvider"],
    )
    app.prepare(ctx_id=-1, det_thresh=0.5, det_size=(640, 640))

    model_dir = MODEL_ROOT / "models" / "buffalo_l"
    model_files = {
        name: {"path": f"~/.insightface/{path.relative_to(MODEL_ROOT)}", "sha256": sha256(path)}
        for name, path in {
            "detector": model_dir / "det_10g.onnx",
            "recognition": model_dir / "w600k_r50.onnx",
        }.items()
    }

    references = {}
    detections = []
    for person in PEOPLE:
        path = ROOT / f"reference-{person}.png"
        embedding, detection = select_single_face(app, path)
        references[person] = embedding
        detections.append({"image": str(path.relative_to(ROOT)), **detection})

    rows = []
    for person in PEOPLE:
        for seed in SEEDS:
            for mode in MODES:
                path = ROOT / "generated" / f"{person}-{seed}-{mode}-s3" / "output.png"
                embedding, detection = select_single_face(app, path)
                similarity = float(np.dot(references[person], embedding))
                rows.append(
                    {
                        "person": person,
                        "seed": seed,
                        "mode": mode,
                        "cosine_similarity": similarity,
                        "cosine_distance": 1.0 - similarity,
                        "image": str(path.relative_to(ROOT)),
                        **detection,
                    }
                )
                detections.append({"image": str(path.relative_to(ROOT)), **detection})

    pairs = []
    for person in PEOPLE:
        for seed in SEEDS:
            pair = {r["mode"]: r for r in rows if r["person"] == person and r["seed"] == seed}
            regenerate = pair["regenerate"]["cosine_similarity"]
            sequential = pair["sequential"]["cosine_similarity"]
            pairs.append(
                {
                    "person": person,
                    "seed": seed,
                    "regenerate_similarity": regenerate,
                    "sequential_similarity": sequential,
                    "regenerate_minus_sequential": regenerate - sequential,
                    "winner": "regenerate" if regenerate > sequential else "sequential" if sequential > regenerate else "tie",
                }
            )

    means = {
        mode: float(np.mean([r["cosine_similarity"] for r in rows if r["mode"] == mode]))
        for mode in MODES
    }
    per_person = {
        person: {
            mode: float(np.mean([r["cosine_similarity"] for r in rows if r["person"] == person and r["mode"] == mode]))
            for mode in MODES
        }
        for person in PEOPLE
    }
    cross_identity = [
        float(np.dot(references[a], references[b])) for a, b in combinations(PEOPLE, 2)
    ]
    result = {
        "method": {
            "library": "insightface",
            "library_version": "0.7.3",
            "model_pack": "buffalo_l",
            "recognition_model": "w600k_r50.onnx",
            "embedding_dimensions": 512,
            "detector": "det_10g.onnx",
            "det_size": [640, 640],
            "det_thresh": 0.5,
            "providers": ["CPUExecutionProvider"],
            "model_files": model_files,
            "pretrained_model_license": "non-commercial research only",
        },
        "images": len(detections),
        "references": len(references),
        "final_outputs": len(rows),
        "paired_comparisons": len(pairs),
        "all_images_single_face": all(d["det_score"] >= 0.5 for d in detections),
        "minimum_detection_score": min(d["det_score"] for d in detections),
        "means": means,
        "mean_difference_regenerate_minus_sequential": means["regenerate"] - means["sequential"],
        "regenerate_wins": sum(p["winner"] == "regenerate" for p in pairs),
        "sequential_wins": sum(p["winner"] == "sequential" for p in pairs),
        "per_person_means": per_person,
        "per_person_regenerate_wins": sum(v["regenerate"] > v["sequential"] for v in per_person.values()),
        "different_identity_reference_similarity": {
            "pairs": len(cross_identity),
            "mean": float(np.mean(cross_identity)),
            "maximum": float(np.max(cross_identity)),
        },
        "rows": rows,
        "pairs": pairs,
        "detections": detections,
    }
    (ROOT / "arcface-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    with (ROOT / "arcface-pairs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(pairs[0]))
        writer.writeheader()
        writer.writerows(pairs)

    verification = {
        "passed": len(rows) == 36 and len(pairs) == 18 and result["all_images_single_face"],
        "images_checked": len(detections),
        "single_face_images": len(detections),
        "paired_comparisons": len(pairs),
        "model_files": model_files,
        "analysis_sha256": sha256(Path(__file__)),
        "results_sha256": sha256(ROOT / "arcface-results.json"),
        "csv_sha256": sha256(ROOT / "arcface-pairs.csv"),
    }
    (ROOT / "arcface-verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ["means", "mean_difference_regenerate_minus_sequential", "regenerate_wins", "sequential_wins", "per_person_regenerate_wins", "minimum_detection_score"]}, indent=2))


if __name__ == "__main__":
    main()
