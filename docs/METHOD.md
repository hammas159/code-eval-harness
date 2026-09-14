# Method

[<- back to README](../README.md)

## Generate once, score many ways

Generation and scoring are deliberately separate. Each solution is generated exactly once
per (model, problem) and cached to disk as JSON.

That means **adding a sixth extraction strategy and re-scoring every problem costs no model
time at all** - which is the whole point of the design, and what makes the comparison
honest: every strategy sees byte-identical output.

## Generation settings

| Setting | Value |
|---|---|
| Temperature | 0 |
| Seed | 0 |
| `num_predict` | 420 |
| Prompt | "Complete this Python function. Reply with the complete function." + the HumanEval prompt |

Greedy decoding means this is pass@1 at temperature 0, not an estimate of pass@k.

## The five extraction strategies

| Strategy | What it does | What it assumes |
|---|---|---|
| `raw` | use the output verbatim | the model emits nothing but code |
| `prompt+body` | `prompt + output` | the model **continues** the signature - the original HumanEval protocol, written for completion models |
| `first_fence` | take the first ``` block | the answer is in one fenced block |
| `all_fences` | concatenate every ``` block | imports may be split from the function |
| `smart` | all fences, then prepend the prompt if no `def` is present | handles both chat and completion shapes |

## Execution

Candidate code is written to a temp directory and run in a **separate process** with a
12-second timeout, against HumanEval's own `check()` function.

The entry point is interpolated **bare**, not as `repr()`. HumanEval's `check` takes the
function object, so `repr()` silently passes the *name as a string* and every test fails
with `'str' object is not callable` regardless of whether the code was correct. That bug
shipped in the first version of this harness - see [PROBLEMS.md](PROBLEMS.md).

## Safety

The subprocess and timeout are a **guard, not a sandbox**. The process is killed on
overrun and runs in a throwaway directory, but nothing prevents a generation from touching
the filesystem or the network. See [LIMITATIONS.md](LIMITATIONS.md).

## Data

`openai/openai_humaneval` (164 problems, 0.1 MB), read from the local Hugging Face cache.
Cache resolution is `HF_HUB_CACHE`, then `HF_HOME/hub`, then the platform default.
