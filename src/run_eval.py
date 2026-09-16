"""Generate solutions once per (model, problem), then score them under every strategy.

Writes results/scores.json. Generation is cached on disk, so re-running to add a new
extraction strategy costs no model time at all.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import STRATEGIES, generate, load_problems, run_tests

RESULTS = Path(__file__).resolve().parent.parent / "results"
MODELS = ["qwen2.5-coder:3b", "qwen2.5:7b-instruct", "qwen2.5-coder:14b"]


def main(limit: int = 50, models: list[str] | None = None) -> None:
    models = models or MODELS
    problems = load_problems(limit)
    RESULTS.mkdir(exist_ok=True)
    print(f"problems: {len(problems)}   models: {', '.join(models)}")

    records = []
    for model in models:
        for i, problem in enumerate(problems, 1):
            try:
                output = generate(model, problem)
            except Exception as exc:  # noqa: BLE001 - a dead model should not lose the run
                print(f"  [{model}] {problem.task_id} generation failed: {type(exc).__name__}")
                continue

            row = {"model": model, "task_id": problem.task_id, "chars": len(output)}
            for name, strategy in STRATEGIES.items():
                ok, detail = run_tests(strategy(problem.prompt, output), problem)
                row[name] = ok
                row[f"{name}__why"] = detail
            records.append(row)
            marks = "".join("P" if row[s] else "." for s in STRATEGIES)
            print(f"  [{model:20}] {i:3}/{len(problems)} {problem.task_id:18} {marks}")

    RESULTS.joinpath("scores.json").write_text(
        json.dumps({"models": models, "n_problems": len(problems), "records": records}, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'model':22} " + "  ".join(f"{s:>12}" for s in STRATEGIES))
    print("-" * (22 + 14 * len(STRATEGIES)))
    for model in models:
        rows = [r for r in records if r["model"] == model]
        if not rows:
            continue
        cells = "  ".join(f"{sum(r[s] for r in rows) / len(rows):>11.1%}" for s in STRATEGIES)
        print(f"{model:22} {cells}")

    # The headline: same generations, different harness, different answer.
    for model in models:
        rows = [r for r in records if r["model"] == model]
        if not rows:
            continue
        rates = {s: sum(r[s] for r in rows) / len(rows) for s in STRATEGIES}
        best, worst = max(rates.values()), min(rates.values())
        print(
            f"\n{model}: best {best:.1%} vs worst {worst:.1%} -> "
            f"spread of {best - worst:.1%} from extraction alone "
            f"({len(rows)} problems, identical generations)"
        )


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    main(n)
