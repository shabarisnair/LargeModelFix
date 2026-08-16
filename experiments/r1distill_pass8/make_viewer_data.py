"""Pack dags.jsonl into a compact JSON blob for the DAG viewer artifact.

Ships both graphs:
  raw     -- one node per reasoning step
  merged  -- linear `continue` runs collapsed into super-nodes, which is what makes a
             200-step trace readable as a tree
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in open(HERE / "reasoning_dags" / "dags.jsonl") if l.strip()]


def pack_raw(raw, n):
    return {
        "n": n,
        "parents": [raw["parents"].get(str(i), []) for i in range(n)],
        "actions": [raw["actions"].get(str(i), "") for i in range(n)],
        "depth": [raw["depth"].get(str(i), 0) for i in range(n)],
        "text": [raw["node_texts"].get(str(i), "") for i in range(n)],
        "why": [raw["explanations"].get(str(i), "") for i in range(n)],
    }


def pack_merged(m):
    nodes = m.get("merged_nodes", [])
    ids = [nd["id"] for nd in nodes]
    idx = {nid: k for k, nid in enumerate(ids)}
    members = [nd["raw"] for nd in nodes]
    parents = []
    for nid in ids:
        ps = m["parents"].get(str(nid), [])
        parents.append([idx[p] for p in ps if p in idx])
    return {
        "n": len(ids),
        "parents": parents,
        "actions": [m["actions"].get(str(nid), "") for nid in ids],
        "members": members,
        "label": [f"s{mem[0]}" if len(mem) == 1 else f"s{mem[0]}–s{mem[-1]}"
                  for mem in members],
    }


out = []
for r in rows:
    n = r["n_steps"]
    out.append({
        "dataset": r["dataset"], "qid": r["id"], "model": r["model"],
        "seed": r["seed"], "correct": bool(r["correct"]),
        "leaves": r["dag_graph_raw"].get("leaves", []),
        "raw": pack_raw(r["dag_graph_raw"], n),
        "merged": pack_merged(r["dag_graph_merged"]),
    })

payload = json.dumps(out, separators=(",", ":"))
(HERE / "reasoning_dags" / "viewer_data.json").write_text(payload)
print(f"{len(out)} traces, {len(payload):,} bytes")
for t in out[:3]:
    print(f"  {t['qid']:20s} {t['model']:5s} raw={t['raw']['n']:4d} "
          f"merged={t['merged']['n']:4d}")
