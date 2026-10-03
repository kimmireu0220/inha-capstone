"""Check manuscript values and table rows against the cited experiments."""

from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
manuscript = (PAPER / "manuscript.ko.md").read_text()
sources = {
    "synthetic_policy": "experiments/studio-multiperson-v1/results.json",
    "synthetic_arcface": "experiments/studio-multiperson-v1/arcface-results.json",
    "real_policy_pilot": "experiments/real-people-v1/results.json",
    "prompt_synthesis": "experiments/prompt-synthesis-expanded-v1/summary.json",
    "automatic_state": "experiments/state-tracking-v2/summary.json",
}
data = {key: json.loads((ROOT / path).read_text()) for key, path in sources.items()}
checked = []


def expect(value, precision=6):
    token = f"{value:.{precision}f}" if isinstance(value, float) else str(value)
    assert token in manuscript, f"Manuscript missing {token}"
    checked.append(token)


def expect_row(cells):
    line = '| ' + ' | '.join(str(cell) for cell in cells) + ' |'
    assert line in manuscript.splitlines(), f'Manuscript table missing exact row: {line}'
    checked.append(line)


policy = data["synthetic_policy"]
face = data["synthetic_arcface"]
assert policy["complete"] and policy["paired_comparisons"] == 18
assert face["paired_comparisons"] == 18 and face["regenerate_wins"] == 18
for mode in ("regenerate", "sequential"):
    for metric in ("lpips", "ssim"):
        expect(policy["means"][mode][metric])
    expect(face["means"][mode])

real = data["real_policy_pilot"]
assert real["complete"] and real["paired_comparisons"] == 2
for row in real["rows"]:
    if row["stage"] == 3:
        expect(row["identity_similarity"])

prompt = data["prompt_synthesis"]
assert prompt["outputs"] == 108 and prompt["independent_people"] == 6
for mode in ("history", "agent", "state"):
    row = prompt["by_mode"][mode]
    expect(row["achieved"])
    expect(row["identity_mean"])
    for history in ("H1", "H2", "H3"):
        expect(prompt["by_history"][history][mode]["achieved"])
for person in prompt["by_person"].values():
    assert person["agent"]["achieved"] > person["history"]["achieved"]
    assert person["agent"]["identity_mean"] < person["history"]["identity_mean"]
    assert person["agent"]["identity_mean"] < person["state"]["identity_mean"]
    for mode in ("history", "agent"):
        expect(f'{person[mode]["achieved"]}/36')
        expect(person[mode]["identity_mean"], 3)

automatic = data['automatic_state']
for name, digest in automatic['source_sha256'].items():
    assert hashlib.sha256((ROOT / 'experiments/state-tracking-v2' / name).read_bytes()).hexdigest() == digest, \
        f'Automatic-state summary is stale: {name}'
assert automatic['complete'] and automatic['outputs'] == 96 and automatic['pairs'] == 48
assert automatic['independent_people'] == 6
assert automatic['rater_type'] == 'AI' and automatic['independent_human_rating_complete'] is False
for mode, label in [('agent', '에이전트 종합'), ('tracked', '자동 상태 갱신')]:
    primary = automatic['by_mode'][mode]
    secondary = automatic['second_ai']['by_mode'][mode]
    assert primary['images'] == secondary['images'] == 48
    assert primary['target_total'] == secondary['target_total'] == 288
    expect_row([label, f"{primary['achieved']}/288", f"{secondary['achieved']}/288",
                f"{primary['cancelled_achieved']}/{primary['cancelled_total']}",
                f"{primary['identity_mean']:.6f}"])
for person, modes in automatic['by_person'].items():
    expect_row([person, f"{modes['agent']['achieved']}/48", f"{modes['tracked']['achieved']}/48",
                f"{modes['agent']['identity_mean']:.3f}", f"{modes['tracked']['identity_mean']:.3f}"])
state = automatic['state_extraction']
for numerator, denominator in [('correct_slots', 'total_slots'), ('changed_correct', 'changed_total'),
                               ('final_correct_slots', 'final_total_slots'),
                               ('joint_correct_turns', 'total_turns'),
                               ('joint_correct_final_dialogues', 'total_dialogues')]:
    expect(f'{state[numerator]}/{state[denominator]}')
agreement = automatic['second_ai']['agreement']
expect(f"{agreement['same']}/{agreement['comparable']}")

evidence = {
    "date": "2026-10-03",
    "passed": True,
    "scope": "Numeric transcription and source-hash checks, not independent scientific validation",
    "manuscript_sha256": hashlib.sha256(manuscript.encode()).hexdigest(),
    "checked_values": checked,
    "sources": [
        {"name": name, "path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
        for name, path in sources.items()
    ],
}
(PAPER / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
print(f"Paper audit passed: {len(checked)} values/rows and {len(sources)} source files")
