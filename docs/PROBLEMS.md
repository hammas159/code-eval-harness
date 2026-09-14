# Problems hit while building this

[<- back to README](../README.md)

## 1. The harness scored working models at 0%

The runner template interpolated `repr(entry_point)`, so HumanEval's `check()` received the
**string** `"add"` instead of the function object. Every test failed with
`'str' object is not callable` - no matter how correct the generated code was.

The first full run reported **0% for every model under every strategy.** The models were
answering correctly the entire time.

**This is precisely the failure this repository exists to measure**, and it happened here
first. It was caught because 0% across the board on easy problems is not a plausible
result, not because a test failed.

**Fix:** interpolate the bare name. `test_entry_point_is_passed_as_a_function_not_a_string`
is named after the bug.

## 2. Two results looked like two findings

`raw` and `prompt+body` both scored 0%, which reads as two independent failure modes.

**What was done:** checked the actual failure reasons rather than reporting the table as-is.
**100 of 100 `SyntaxError` for each, same cause.** The README now says so explicitly rather
than letting a five-column table imply five independent results.

## 3. `plotly` was unavailable

The charts were written for plotly, which was not installed, and the connection at the time
was too slow to fetch it.

**Fix:** rewrote them in **Altair**, which ships with Streamlit - zero download, and the
charts are arguably better for this data.

## 4. Unicode crash on Windows

Printing a non-ASCII character to a `cp1252` console killed an inspection script mid-run.

**Fix:** `PYTHONIOENCODING=utf-8`, and non-ASCII kept out of program output.

## 5. Buffered logs hid all progress

Redirecting stdout to a file meant nothing appeared for minutes at a time, making a long
run indistinguishable from a hung one.

**Fix:** tracked progress by counting cached generation files instead of watching the log.

## 6. CI cache misconfigured

`setup-uv` errors outright when its default `**/uv.lock` glob matches nothing.

**Fix:** keyed the cache on `pyproject.toml`.
