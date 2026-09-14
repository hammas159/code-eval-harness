# Results

[<- back to README](../README.md)

HumanEval problems 0-49, greedy decoding (temperature 0, fixed seed), one generation per
(model, problem), cached on disk.

## pass@1 by model and extraction strategy

| Model | `raw` | `prompt+body` | `first_fence` | `all_fences` | `smart` |
|---|---:|---:|---:|---:|---:|
| qwen2.5-coder:3b | **0.0%** | **0.0%** | 94.0% | 94.0% | 94.0% |
| qwen2.5:7b-instruct | **0.0%** | **0.0%** | 94.0% | 94.0% | 94.0% |

**Spread: 94 percentage points**, with the generations held identical.

## Why the two zeros are one finding

| Strategy | Failures | Cause |
|---|---:|---|
| `raw` | 100 / 100 | `SyntaxError` |
| `prompt+body` | 100 / 100 | `SyntaxError` |

Every single failure in both strategies is a syntax error, and the cause is the same: the
models wrap their answers in ```` ```python ```` fences, and backticks are not Python.

So the table shows **one finding with two faces**, not five independent results:

1. **`raw`** - using the output verbatim fails whenever the model writes markdown.
2. **`prompt+body`** - *the original HumanEval protocol.* It treats the output as a
   continuation of the function signature, which is correct for **completion** models. A
   chat-tuned model restates the whole function inside a fence, so the concatenation is
   invalid Python.

The second is the substantive point. A harness written for completion models scores modern
chat models at zero - not because they cannot code, but because the protocol assumes an
output shape they no longer produce. **The failure is silent: it looks like a model result,
not a harness result.**

## Model comparison

Under `smart`, the two models disagree on **2 of 50 problems**: `HumanEval/19` and
`HumanEval/38`.

Problems failed by both models under `smart`: `HumanEval/19`, `HumanEval/26`,
`HumanEval/32`, `HumanEval/38`.

**2.3x the parameters produced no measurable difference** on this subset.

## Raw data

`results/scores.json` contains one record per (model, problem) with the pass/fail and the
failure reason under every strategy. Cached generations are in `generations/`, one JSON per
(model, problem), so any new strategy can be scored without re-running a model.

## Reproducing

```bash
python src/run_eval.py 50
streamlit run ui/app.py
```

Generations are cached, so a second run scores instantly.
