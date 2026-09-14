# Future work

[<- back to README](../README.md)

## 1. Run the full 164 problems

The current 50 are the easier half, which is why the README says the numbers are not
comparable to published pass@1. Running all 164 costs roughly three times the generation
time and removes that caveat entirely.

## 2. Add a larger model

The comparison code is written and generations are cached, so adding `qwen2.5-coder:14b`
is **one command**. The interesting question is whether it moves the `smart` score at all,
given that 3B and 7B are already indistinguishable here.

## 3. pass@k with sampling

Temperature above 0, several samples per problem. That is what published numbers report,
and it would show whether the extraction spread is stable across samples or an artefact of
greedy decoding.

## 4. Add MBPP

Already downloaded (0.8 MB). It would answer whether the extraction spread is specific to
HumanEval's prompt format or general to code benchmarks.

## 5. A real sandbox

Containerisation or `seccomp` would make it safe to run untrusted generations. Currently
the subprocess and timeout are a guard against runaway code, not against malice.

## 6. Treat the prompt as a variable too

Prompt phrasing is a **second unreported free parameter**, and the same
generate-once/score-many design would measure it - though it needs regeneration per prompt,
so it is more expensive than varying extraction.

## 7. Publish a recommended extraction standard

The practical output of this work: if pass@1 numbers are to be comparable between papers,
the extraction rule has to be stated. A reference implementation plus a recommended default
would be more useful than the measurement alone.
