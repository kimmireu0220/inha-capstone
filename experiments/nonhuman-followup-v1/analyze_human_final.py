#!/usr/bin/env python3
"""Validate and decode final-output human ratings without exposing labels in the survey."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
KEY_PATH = ROOT / "private" / "requirements-key.json"
FACE_PATH = ROOT / "joined-reviews" / "face.json"
METRICS_PATH = ROOT / "extension-metrics" / "results.json"
RESPONSES = ROOT / "human-responses"
OUT_DIR = ROOT / "human-analysis"
VALID = {"0", "1", "2", "3", "unknown"}
VALID_PRESERVATION = {"0", "1", "2", "unknown"}


def policy(sources: list[str]) -> str:
    if len(sources) > 1 and any("triggered" in source for source in sources):
        return "shared_rebase_final"
    if any("fixed3" in source for source in sources):
        return "fixed_interval_3"
    if any("once-triggered" in source for source in sources):
        return "trigger_once"
    if all("end-only" in source or "always-original" in source for source in sources):
        return "end_regeneration"
    return "sequential"


def auc(scores: list[float], labels: list[bool]) -> float | None:
    positive = [score for score, label in zip(scores, labels) if label]
    negative = [score for score, label in zip(scores, labels) if not label]
    if not positive or not negative:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in positive for n in negative)
    return wins / (len(positive) * len(negative))


def ranks(values: list[float]) -> list[float]:
    result = [0.0] * len(values)
    ordered = sorted(range(len(values)), key=values.__getitem__)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        average = (start + 1 + end) / 2
        for index in ordered[start:end]:
            result[index] = average
        start = end
    return result


def spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    x, y = ranks(left), ranks(right)
    x_mean, y_mean = sum(x) / len(x), sum(y) / len(y)
    numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y))
    denominator = math.sqrt(
        sum((a - x_mean) ** 2 for a in x) * sum((b - y_mean) ** 2 for b in y)
    )
    return numerator / denominator if denominator else None


def main() -> None:
    key_rows = json.loads(KEY_PATH.read_text())
    key = {row["id"]: row for row in key_rows}
    face = json.loads(FACE_PATH.read_text())["unique_outputs"]
    metric_rows = json.loads(METRICS_PATH.read_text())["rows"]
    agent_by_sha = {
        row["output_sha256"]: row["ratings"]
        for row in face.values()
    }

    rows: list[dict[str, object]] = []
    seen_sessions: set[tuple[str, str]] = set()
    for path in sorted(RESPONSES.glob("current-final-human-v1-face-*.json")):
        data = json.loads(path.read_text())
        if data.get("schema") != "current-final-human-v1" or data.get("mode") != "face":
            raise ValueError(f"wrong schema or mode: {path}")
        rater = data.get("rater")
        session = (str(rater), str(data.get("submittedAt")))
        if session in seen_sessions:
            raise ValueError(f"duplicate session: {session}")
        seen_sessions.add(session)
        responses = data.get("responses", [])
        if len(responses) != len(key):
            raise ValueError(f"{path}: expected {len(key)} responses, got {len(responses)}")
        candidate_ids = [response.get("candidate") for response in responses]
        if len(candidate_ids) != len(set(candidate_ids)) or set(candidate_ids) != set(key):
            raise ValueError(f"{path}: candidate set is incomplete or duplicated")
        for response in responses:
            candidate = str(response["candidate"])
            value = str(response["answer"]["value"])
            if value not in VALID:
                raise ValueError(f"{path}: invalid answer {value}")
            meta = key[candidate]
            agents = agent_by_sha.get(meta["output_sha256"], {})
            metric = metric_rows[f'{meta["reference_sha256"]}:{meta["output_sha256"]}']["face"]
            rows.append({
                "rater": rater,
                "submitted_at": data.get("submittedAt"),
                "candidate": candidate,
                "policy": policy(meta["sources"]),
                "sources": "+".join(meta["sources"]),
                "human_severity": value,
                "human_clear": "" if value == "unknown" else int(value) >= 2,
                "agent_a_severity": agents.get("a", {}).get("severity", ""),
                "agent_b_severity": agents.get("b", {}).get("severity", ""),
                "fixed_mae": metric["fixed"]["mae"],
                "fixed_ssim": metric["fixed"]["ssim"],
                "fixed_lpips": metric["fixed"]["lpips"],
                "aligned_mae": metric["3"]["mae"],
                "aligned_ssim": metric["3"]["ssim"],
                "aligned_lpips": metric["3"]["lpips"],
            })

    OUT_DIR.mkdir(exist_ok=True)
    columns = list(rows[0]) if rows else []
    with (OUT_DIR / "decoded-face.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, object] = {
        "sessions": len(seen_sessions),
        "ratings": len(rows),
        "overall": dict(sorted(Counter(str(row["human_severity"]) for row in rows).items())),
        "by_policy": {},
        "agent_agreement": {},
        "threshold_free": {},
    }
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["policy"])].append(row)
    for name, group in sorted(grouped.items()):
        known = [row for row in group if row["human_severity"] != "unknown"]
        summary["by_policy"][name] = {
            "n": len(group),
            "severity_counts": dict(sorted(Counter(str(row["human_severity"]) for row in group).items())),
            "clear_rate": sum(bool(row["human_clear"]) for row in known) / len(known) if known else None,
            "mean_severity": sum(int(str(row["human_severity"])) for row in known) / len(known) if known else None,
        }
    for agent in ("a", "b"):
        comparable = [row for row in rows if row["human_severity"] != "unknown" and row[f"agent_{agent}_severity"] != ""]
        exact = sum(int(str(row["human_severity"])) == int(row[f"agent_{agent}_severity"]) for row in comparable)
        binary = sum((int(str(row["human_severity"])) >= 2) == (int(row[f"agent_{agent}_severity"]) >= 2) for row in comparable)
        summary["agent_agreement"][agent] = {
            "n": len(comparable),
            "exact": exact,
            "exact_rate": exact / len(comparable) if comparable else None,
            "clear_binary": binary,
            "clear_binary_rate": binary / len(comparable) if comparable else None,
        }

    known_rows = [row for row in rows if row["human_severity"] != "unknown"]
    labels = [bool(row["human_clear"]) for row in known_rows]
    severity = [float(str(row["human_severity"])) for row in known_rows]
    for prefix in ("fixed", "aligned"):
        for metric_name in ("mae", "ssim", "lpips"):
            field = f"{prefix}_{metric_name}"
            scores = [float(row[field]) for row in known_rows]
            if metric_name == "ssim":
                scores = [1.0 - score for score in scores]
            summary["threshold_free"][f"{prefix}_{metric_name}_auc"] = auc(scores, labels)
            summary["threshold_free"][f"{prefix}_{metric_name}_spearman"] = spearman(scores, severity)

    pair_bases = ("P01", "P02", "P03-r1", "P03-r2", "P04", "P05", "P06")
    row_by_candidate = {str(row["candidate"]): row for row in rows}
    pairs: list[tuple[dict[str, object], dict[str, object]]] = []
    for base in pair_bases:
        sequential_id = next(row["id"] for row in key_rows if base in row["sources"])
        regenerated_id = next(row["id"] for row in key_rows if f"{base}-end-only" in row["sources"])
        pairs.append((row_by_candidate[sequential_id], row_by_candidate[regenerated_id]))
    summary["threshold_free"]["paired_sequential_vs_end_regeneration"] = {
        "n": len(pairs),
        **{
            f"{prefix}_{metric_name}_sequential_higher": sum(
                (float(sequential[f"{prefix}_{metric_name}"]) > float(regenerated[f"{prefix}_{metric_name}"]))
                if metric_name != "ssim" else
                (float(sequential[f"{prefix}_{metric_name}"]) < float(regenerated[f"{prefix}_{metric_name}"]))
                for sequential, regenerated in pairs
            )
            for prefix in ("fixed", "aligned")
            for metric_name in ("mae", "ssim", "lpips")
        },
    }

    preservation_rows: list[dict[str, object]] = []
    preservation_sessions: set[tuple[str, str]] = set()
    for path in sorted(RESPONSES.glob("current-final-human-v2-requirements-*.json")):
        data = json.loads(path.read_text())
        if data.get("schema") != "current-final-human-v2" or data.get("mode") != "requirements":
            raise ValueError(f"wrong schema or mode: {path}")
        rater = str(data.get("rater"))
        session = (rater, str(data.get("submittedAt")))
        if session in preservation_sessions:
            raise ValueError(f"duplicate session: {session}")
        preservation_sessions.add(session)
        responses = data.get("responses", [])
        candidate_ids = [response.get("candidate") for response in responses]
        if len(responses) != len(key) or len(candidate_ids) != len(set(candidate_ids)) or set(candidate_ids) != set(key):
            raise ValueError(f"{path}: candidate set is incomplete or duplicated")
        face_by_candidate = {
            str(row["candidate"]): row
            for row in rows
            if str(row["rater"]) == rater
        }
        for response in responses:
            candidate = str(response["candidate"])
            value = str(response["answer"]["value"])
            if value not in VALID_PRESERVATION or response.get("kind") != "face_preservation":
                raise ValueError(f"{path}: invalid preservation response")
            meta = key[candidate]
            face_row = face_by_candidate.get(candidate)
            preservation_rows.append({
                "rater": rater,
                "submitted_at": data.get("submittedAt"),
                "candidate": candidate,
                "policy": policy(meta["sources"]),
                "sources": "+".join(meta["sources"]),
                "preservation": value,
                "preservation_failed": "" if value == "unknown" else int(value) == 0,
                "face_severity": face_row["human_severity"] if face_row else "",
                "face_clear": face_row["human_clear"] if face_row else "",
            })

    preservation_summary: dict[str, object] = {
        "sessions": len(preservation_sessions),
        "ratings": len(preservation_rows),
        "overall": dict(sorted(Counter(str(row["preservation"]) for row in preservation_rows).items())),
        "by_policy": {},
        "paired_with_face": {},
    }
    preservation_grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in preservation_rows:
        preservation_grouped[str(row["policy"])].append(row)
    for name, group in sorted(preservation_grouped.items()):
        known = [row for row in group if row["preservation"] != "unknown"]
        preservation_summary["by_policy"][name] = {
            "n": len(group),
            "preservation_counts": dict(sorted(Counter(str(row["preservation"]) for row in group).items())),
            "failed_rate": sum(bool(row["preservation_failed"]) for row in known) / len(known) if known else None,
            "mean_preservation": sum(int(str(row["preservation"])) for row in known) / len(known) if known else None,
        }
    paired = [
        row for row in preservation_rows
        if row["preservation"] != "unknown" and row["face_clear"] != ""
    ]
    paired_agreement = sum(bool(row["preservation_failed"]) == bool(row["face_clear"]) for row in paired)
    preservation_summary["paired_with_face"] = {
        "n": len(paired),
        "clear_face_equals_failed_preservation": paired_agreement,
        "rate": paired_agreement / len(paired) if paired else None,
        "note": "Same-rater paired descriptions; not independent validation.",
    }

    preservation_columns = list(preservation_rows[0]) if preservation_rows else []
    with (OUT_DIR / "decoded-preservation.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=preservation_columns)
        writer.writeheader()
        writer.writerows(preservation_rows)

    (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (OUT_DIR / "summary-preservation.json").write_text(json.dumps(preservation_summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"face": summary, "preservation": preservation_summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
