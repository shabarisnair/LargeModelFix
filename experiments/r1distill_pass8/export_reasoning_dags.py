"""Summarise the reasoning DAGs and export a readable per-query 32B vs 1.5B comparison.

    python export_reasoning_dags.py

Reads reasoning_dags/dags.jsonl and writes, into the same folder:
  README.md              aggregate structure stats + per-query comparison table
  <dataset>/<id>.md      per-query side-by-side, with a mermaid diagram when small
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
MERMAID_MAX_NODES = 40      # bigger graphs are unreadable as diagrams


def stats(row: dict) -> dict:
    raw = row["dag_graph_raw"]
    acts = collections.Counter(raw["actions"].values())
    n = row["n_steps"]
    depth = max(int(v) for v in raw["depth"].values()) if raw["depth"] else 0
    merged = row["dag_graph_merged"]
    return {
        "steps": n,
        "continue": acts.get("continue", 0),
        "backtrack": acts.get("backtrack", 0),
        "merge": acts.get("merge", 0),
        # share of non-root steps that abandon the current line of reasoning
        "backtrack_rate": acts.get("backtrack", 0) / max(n - 1, 1),
        "max_depth": depth,
        "leaves": len(raw.get("leaves", [])),
        "supernodes": len(merged.get("merged_nodes", [])),
        # linearity: a purely sequential trace has depth == steps-1 and one leaf
        "linearity": depth / max(n - 1, 1),
        "errors": len(row.get("dag_parse_errors", [])),
        "calls": row.get("dag_usage", {}).get("calls", 0),
    }


def mermaid(row: dict) -> list[str]:
    raw = row["dag_graph_raw"]
    parents = {int(k): v for k, v in raw["parents"].items()}
    if len(parents) > MERMAID_MAX_NODES:
        return []
    acts = {int(k): v for k, v in raw["actions"].items()}
    out = ["```mermaid", "graph TD"]
    for node, plist in sorted(parents.items()):
        out.append(f"  s{node}[\"s{node}\"]")
        for p in plist:
            style = {"backtrack": "-.->", "merge": "==>"}.get(acts.get(node), "-->")
            out.append(f"  s{p} {style} s{node}")
    out.append("```")
    out.append("")
    out.append("`-->` continue &nbsp;&nbsp; `-.->` backtrack &nbsp;&nbsp; `==>` merge")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dags", default=str(HERE / "reasoning_dags" / "dags.jsonl"))
    args = ap.parse_args()

    path = Path(args.dags)
    rows = [json.loads(l) for l in open(path) if l.strip()]
    rows = [r for r in rows if "dag_graph_raw" in r]
    if not rows:
        raise SystemExit("no completed DAG rows yet")
    out = path.parent

    by_key = {(r["dataset"], r["id"], r["model"]): r for r in rows}
    S = {k: stats(r) for k, r in by_key.items()}

    # aggregate per dataset x model
    agg = collections.defaultdict(list)
    for (ds, _qid, model), s in S.items():
        agg[(ds, model)].append(s)

    lines = ["# Reasoning DAGs (TRM method)", "",
             "Dependency DAGs over the **thinking-block** steps of the v1 traces sampled in",
             "`trace_samples/`, built with the reference implementation in",
             "`experiments/post_trace_dag/TRM/dag_construction`.", "",
             "## Method", "",
             "For each step the judge LLM classifies how it attaches to earlier steps:", "",
             "- **continue** — follows on from the current main path",
             "- **backtrack** — restarts/revisits an earlier step (\"Alternatively…\", \"Let me check again…\")",
             "- **merge** — stitches together two branches", "",
             "`n=3` samples per step, majority-voted and validated (a vote naming an illegal",
             "parent is discarded); linear `continue` chains are then collapsed into",
             "super-nodes for the merged view.", "",
             "**Judge model:** `Qwen/Qwen3-32B` served locally with vLLM, thinking disabled.",
             "The upstream default is `deepseek-v3.2` via a hosted API; a local judge keeps",
             "the traces on-machine and costs nothing per call. Qwen3's chat template enables",
             "thinking by default, which would consume the 512-token budget before the",
             "`<|action|>` line, so `build_reasoning_dags.py` supplies a custom `ChatClient`",
             "(the extension point the upstream README documents) passing",
             "`chat_template_kwargs={\"enable_thinking\": false}`.", "",
             "## Aggregate structure", "",
             "| dataset | model | traces | median steps | backtrack rate | median depth | median leaves | median super-nodes |",
             "|---|---|---|---|---|---|---|---|"]
    for (ds, model) in sorted(agg):
        v = agg[(ds, model)]
        lines.append(
            f"| {ds} | {model} | {len(v)} | {st.median([x['steps'] for x in v]):.0f} | "
            f"{st.median([x['backtrack_rate'] for x in v])*100:.0f}% | "
            f"{st.median([x['max_depth'] for x in v]):.0f} | "
            f"{st.median([x['leaves'] for x in v]):.0f} | "
            f"{st.median([x['supernodes'] for x in v]):.0f} |")

    lines += ["", "**backtrack rate** = share of non-root steps classified `backtrack`.",
              "**leaves** = dangling branches never folded back in — abandoned lines of",
              "reasoning. A perfectly linear trace has 1 leaf and depth = steps-1.", "",
              "## Per query", "",
              "| dataset | query | model | steps | cont | back | merge | depth | leaves | super-nodes | linearity |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for (ds, qid, model) in sorted(S):
        s = S[(ds, qid, model)]
        lines.append(f"| {ds} | `{qid}` | {model} | {s['steps']} | {s['continue']} | "
                     f"{s['backtrack']} | {s['merge']} | {s['max_depth']} | {s['leaves']} | "
                     f"{s['supernodes']} | {s['linearity']:.2f} |")
    lines += ["", "**linearity** = max_depth / (steps-1); 1.00 is a straight chain, lower",
              "means more branching and abandoned work.", ""]

    total_calls = sum(s["calls"] for s in S.values())
    total_err = sum(s["errors"] for s in S.values())
    lines += [f"Judge calls: {total_calls}. Steps where no valid vote survived (fell back",
              f"to `continue`): {total_err}.", ""]

    # per-query markdown
    for (ds, qid) in sorted({(d, q) for d, q, _ in S}):
        ddir = out / ds
        ddir.mkdir(parents=True, exist_ok=True)
        md = [f"# {ds} — `{qid}` reasoning DAG", "",
              "| model | steps | continue | backtrack | merge | depth | leaves | super-nodes |",
              "|---|---|---|---|---|---|---|---|"]
        for model in ("32B", "1.5B"):
            if (ds, qid, model) not in S:
                continue
            s = S[(ds, qid, model)]
            md.append(f"| {model} | {s['steps']} | {s['continue']} | {s['backtrack']} | "
                      f"{s['merge']} | {s['max_depth']} | {s['leaves']} | {s['supernodes']} |")
        md.append("")
        for model in ("32B", "1.5B"):
            key = (ds, qid, model)
            if key not in S:
                continue
            row, raw = by_key[key], by_key[key]["dag_graph_raw"]
            md += [f"## {model} — seed {row['seed']}, correct={row['correct']}", ""]
            diag = mermaid(row)
            if diag:
                md += diag + [""]
            else:
                md += [f"*({row['n_steps']} steps — too large to draw; see "
                       f"`dags.jsonl` for the full graph.)*", ""]
            acts = {int(k): v for k, v in raw["actions"].items()}
            parents = {int(k): v for k, v in raw["parents"].items()}
            expl = {int(k): v for k, v in raw["explanations"].items()}
            texts = {int(k): v for k, v in raw["node_texts"].items()}
            md += ["### Steps and attachments", "",
                   "| step | action | parents | judge rationale | text |",
                   "|---|---|---|---|---|"]
            for i in sorted(acts)[:60]:
                t = texts.get(i, "").replace("|", "\\|").replace("\n", " ")[:110]
                e = expl.get(i, "").replace("|", "\\|").replace("\n", " ")[:110]
                md.append(f"| s{i} | {acts[i]} | {parents.get(i, [])} | {e} | {t} |")
            if len(acts) > 60:
                md.append(f"| … | | | | *({len(acts)-60} more steps)* |")
            md.append("")
        (out / ds / f"{qid}.md").write_text("\n".join(md))

    (out / "README.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:60]))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
