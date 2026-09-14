"""Generate once, score many ways.

The usual way to report a code benchmark is a single pass@1 number. But between the
model's raw output and that number sits an *extraction step* - pulling the code out of
whatever prose and markdown the model wrapped it in - and that step is a free parameter
almost nobody reports.

So: generate each solution exactly once, cache it, then score the identical generations
under several extraction strategies. Any spread in the results is attributable to the
harness alone, because the model output never changed.
"""

from __future__ import annotations

import glob
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

OLLAMA = "http://localhost:11434/api/generate"
CACHE = Path(__file__).resolve().parent.parent / "generations"


# --- data ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Problem:
    task_id: str
    prompt: str
    test: str
    entry_point: str


def _humaneval_parquet() -> Path | None:
    import os

    roots = []
    if env := os.environ.get("HF_HUB_CACHE"):
        roots.append(Path(env))
    if env := os.environ.get("HF_HOME"):
        roots.append(Path(env) / "hub")
    roots.append(Path.home() / ".cache" / "huggingface" / "hub")
    for root in roots:
        hits = sorted(
            glob.glob(
                str(
                    root
                    / "datasets--openai--openai_humaneval"
                    / "snapshots"
                    / "*"
                    / "**"
                    / "*.parquet"
                ),
                recursive=True,
            )
        )
        if hits:
            return Path(hits[0])
    return None


def load_problems(limit: int | None = None) -> list[Problem]:
    import pandas as pd

    path = _humaneval_parquet()
    if path is None:
        raise FileNotFoundError(
            "HumanEval not in the local Hugging Face cache. Fetch it with:\n"
            '  python -c "from huggingface_hub import hf_hub_download as d; '
            "d('openai/openai_humaneval','openai_humaneval/test-00000-of-00001.parquet',"
            "repo_type='dataset')\""
        )
    frame = pd.read_parquet(path)
    out = [
        Problem(r["task_id"], r["prompt"], r["test"], r["entry_point"]) for _, r in frame.iterrows()
    ]
    return out[:limit] if limit else out


# --- generation ----------------------------------------------------------------------


def generate(model: str, problem: Problem, num_predict: int = 420, timeout: int = 280) -> str:
    """One deterministic completion. Cached on disk so re-scoring costs nothing."""
    CACHE.mkdir(exist_ok=True)
    key = (
        CACHE
        / f"{model.replace(':', '_').replace('/', '_')}__{problem.task_id.replace('/', '_')}.json"
    )
    if key.exists():
        return json.loads(key.read_text(encoding="utf-8"))["response"]

    prompt = f"Complete this Python function. Reply with the complete function.\n\n{problem.prompt}"
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": num_predict, "temperature": 0.0, "seed": 0},
        }
    ).encode()
    request = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    started = time.time()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = json.loads(response.read()).get("response", "")
    key.write_text(
        json.dumps(
            {
                "model": model,
                "task_id": problem.task_id,
                "response": text,
                "seconds": round(time.time() - started, 2),
            }
        ),
        encoding="utf-8",
    )
    return text


# --- extraction: the free parameter this repo is about --------------------------------

FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def extract_raw(prompt: str, output: str) -> str:
    """Use the output verbatim. Fails whenever the model wrote any prose."""
    return output


def extract_fenced(prompt: str, output: str) -> str:
    """Take the first ``` block; fall back to the raw output if there is none."""
    match = FENCE.search(output)
    return match.group(1) if match else output


def extract_fenced_all(prompt: str, output: str) -> str:
    """Concatenate every fenced block - handles imports split from the function."""
    blocks = FENCE.findall(output)
    return "\n".join(blocks) if blocks else output


def extract_prompt_plus_body(prompt: str, output: str) -> str:
    """Treat the output as a *continuation* of the signature, the original HumanEval
    protocol. Correct for completion models, wrong for chat models that restate the
    whole function - which is exactly the mismatch this repo measures."""
    return prompt + output


def extract_smart(prompt: str, output: str) -> str:
    """Fenced if present, then ensure the entry point is actually defined."""
    code = extract_fenced_all(prompt, output)
    if "def " not in code:
        code = prompt + output
    return code


STRATEGIES = {
    "raw": extract_raw,
    "prompt+body": extract_prompt_plus_body,
    "first_fence": extract_fenced,
    "all_fences": extract_fenced_all,
    "smart": extract_smart,
}


# --- execution ------------------------------------------------------------------------

RUNNER = """
import sys
{code}

{test}

check({entry})
print("PASS")
"""


def run_tests(code: str, problem: Problem, timeout: int = 12) -> tuple[bool, str]:
    """Execute candidate code against the reference tests in a separate process.

    SAFETY: this runs code written by a language model. It is confined to a short
    timeout and a throwaway temp directory, and the process is killed on overrun - but
    it is NOT a security sandbox. Do not point this at untrusted generations on a
    machine you care about.
    """
    # The entry point goes in bare: HumanEval's `check` takes the function object, so
    # repr() here silently passes the *name as a string* and every test fails with
    # "'str' object is not callable" regardless of whether the code was correct.
    source = RUNNER.format(code=code, test=problem.test, entry=problem.entry_point)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "candidate.py"
        path.write_text(source, encoding="utf-8")
        try:
            out = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "timeout"
    if out.returncode == 0 and "PASS" in out.stdout:
        return True, "pass"
    error = (out.stderr or "").strip().splitlines()
    return False, (error[-1][:120] if error else f"exit {out.returncode}")
