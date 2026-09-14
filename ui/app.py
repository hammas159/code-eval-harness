"""The same generations, scored five ways.

Every number is read from results/scores.json, which records one cached generation per
(model, problem) and the pass/fail of that identical text under each extraction
strategy. Switch strategy in the sidebar and watch a model's "score" move without a
single token being regenerated.

Run:  streamlit run ui/app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from core import STRATEGIES

st.set_page_config(page_title="code eval harness", layout="wide")

BLUE, RED, GREEN, AMBER, GREY = "#2563eb", "#dc2626", "#16a34a", "#f59e0b", "#94a3b8"

RESULTS = ROOT / "results" / "scores.json"

st.title("The same answers, five different scores")
st.caption(
    "A code benchmark is reported as one number, but between the model's output and "
    "that number sits an **extraction step** - pulling code out of whatever prose and "
    "markdown the model wrapped it in. That step is a free parameter almost nobody "
    "reports. Here each solution was generated **once** and cached; only the extraction "
    "changes."
)

if not RESULTS.exists():
    st.error(f"No results yet. Run:  `python src/run_eval.py 50`\n\nExpected at {RESULTS}")
    st.stop()

payload = json.loads(RESULTS.read_text(encoding="utf-8"))
records = payload["records"]
if not records:
    st.error("results/scores.json has no records.")
    st.stop()

frame = pd.DataFrame(records)
models = payload["models"]
names = list(STRATEGIES)

# --- headline --------------------------------------------------------------------------

rates = {
    m: {s: frame[frame.model == m][s].mean() for s in names}
    for m in models
    if (frame.model == m).any()
}

spreads = {m: max(r.values()) - min(r.values()) for m, r in rates.items()}
worst_model = max(spreads, key=spreads.get)

a, b, c, d = st.columns(4)
a.metric("Problems", payload["n_problems"])
b.metric("Models", len(rates))
c.metric("Extraction strategies", len(names))
d.metric("Largest score spread", f"{spreads[worst_model]:.1%}")

st.error(
    f"**On identical generations, `{worst_model}` scores anywhere from "
    f"{min(rates[worst_model].values()):.1%} to {max(rates[worst_model].values()):.1%} "
    f"— a spread of {spreads[worst_model]:.1%} — depending only on how the code is "
    "pulled out of the output.** The model never changed. Any pass@1 reported without "
    "stating its extraction rule is underdetermined by that much."
)

# --- the matrix --------------------------------------------------------------------------

st.subheader("pass@1 by model and extraction strategy")

grid = pd.DataFrame(
    [{"model": m, "strategy": s, "pass@1": rates[m][s]} for m in rates for s in names]
)

heat = (
    alt.Chart(grid)
    .mark_rect()
    .encode(
        x=alt.X("strategy:N", sort=names, title=None),
        y=alt.Y("model:N", title=None),
        color=alt.Color(
            "pass@1:Q",
            scale=alt.Scale(scheme="blues", domain=[0, 1]),
            legend=alt.Legend(format=".0%"),
        ),
        tooltip=["model", "strategy", alt.Tooltip("pass@1:Q", format=".1%")],
    )
)
labels = heat.mark_text(fontSize=14, fontWeight="bold").encode(
    text=alt.Text("pass@1:Q", format=".1%"),
    color=alt.condition(alt.datum["pass@1"] > 0.5, alt.value("white"), alt.value("#1e293b")),
)
st.altair_chart((heat + labels).properties(height=90 + 60 * len(rates)), width="stretch")

# --- per-model spread ---------------------------------------------------------------------

st.subheader("How far apart the strategies land")
bars = (
    alt.Chart(grid)
    .mark_bar()
    .encode(
        x=alt.X("strategy:N", sort=names, title=None, axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("pass@1:Q", title="pass@1", axis=alt.Axis(format="%")),
        color=alt.Color("strategy:N", sort=names, legend=None),
        column=alt.Column("model:N", title=None),
        tooltip=["model", "strategy", alt.Tooltip("pass@1:Q", format=".1%")],
    )
    .properties(height=300, width=200)
)
st.altair_chart(bars)

# --- disagreements -------------------------------------------------------------------------

st.subheader("Problems where the strategies disagree")
st.caption(
    "These are the cases that make a benchmark number ambiguous: the model wrote one "
    "answer, and whether it counts depends entirely on the harness."
)

frame["n_pass"] = frame[names].sum(axis=1)
split = frame[(frame.n_pass > 0) & (frame.n_pass < len(names))]
st.write(
    f"**{len(split)} of {len(frame)}** (model, problem) pairs are scored "
    f"differently by different strategies."
)

if len(split):
    st.dataframe(
        split[["model", "task_id", *names, "chars"]].reset_index(drop=True),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Inspect one disagreement")
    pick = st.selectbox(
        "Case",
        split.index,
        format_func=lambda i: f"{split.loc[i, 'model']} — {split.loc[i, 'task_id']}",
    )
    row = split.loc[pick]
    cols = st.columns(len(names))
    for col, name in zip(cols, names):
        col.metric(name, "PASS" if row[name] else "FAIL")
        col.caption(str(row.get(f"{name}__why", ""))[:60])

    cached = (
        ROOT
        / "generations"
        / f"{row['model'].replace(':', '_')}__{row['task_id'].replace('/', '_')}.json"
    )
    if cached.exists():
        st.markdown("**What the model actually wrote** (identical for every strategy above)")
        st.code(json.loads(cached.read_text(encoding="utf-8"))["response"], language="python")

st.divider()
st.caption(
    "HumanEval (`openai/openai_humaneval`), greedy decoding (temperature 0, fixed seed), "
    "one generation per (model, problem), cached on disk. Candidate code runs in a "
    "separate process with a timeout - a guard, not a security sandbox."
)
