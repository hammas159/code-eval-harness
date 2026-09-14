# Limitations

[<- back to README](../README.md)

## 94% is not comparable to published pass@1

This is the **first 50 of 164** problems, and HumanEval is roughly ordered by difficulty.
The absolute number would be lower on the full set.

**The purpose is the spread between strategies, not the absolute score.** Do not cite 94%
as a benchmark result.

## One greedy sample per problem

Temperature 0, one generation. This is pass@1 at greedy decoding, **not** an estimate of
pass@k, which is what published numbers usually report and which requires sampling.

## Two models, one family

`qwen2.5-coder:3b` and `qwen2.5:7b-instruct` are both Qwen2.5. The finding that they are
indistinguishable is a statement about these two models on these 50 problems - not a claim
about model scaling in general.

## The extraction spread is partly obvious

`raw` scoring 0% is not surprising: backticks are not Python. The genuinely informative half
is `prompt+body`, because that is the *original benchmark protocol* and its failure is
silent.

The 94-point headline is real but should be read with that in mind - it is the gap between
a naive harness and a correct one, not evidence that five reasonable choices disagree.

## Not a security sandbox

`run_tests` executes model-written code in a subprocess with a timeout, in a temp
directory. That is a **guard against infinite loops, not against malice.** Nothing prevents
filesystem or network access. Do not run untrusted generations with it.

## HumanEval only

Whether this spread is specific to HumanEval's prompt format is untested. MBPP is already
downloaded and would answer it.
