"""One-off probe: how many WebInstruct Integer/Float/MCQ rows are actually machine-checkable?"""
import re, collections
import pyarrow.parquet as pq

T = pq.read_table("/hdd1/ssn899/LargeModelFix/datasets/webinstruct/data/test-00000-of-00001.parquet").to_pylist()

NUM = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)")
SCI = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+))\s*(?:[x×*]\s*10\s*\^?\s*|[eE])\s*([+-]?\d+)")
OPT = re.compile(r"(?:^|[\s|(])([A-E])[\)\.]\s", re.M)


def parse_num(s):
    s = s.strip().replace(",", "").replace("$", "").lstrip("=").strip()
    s = re.sub(r"^\\?\(|\\?\)$", "", s).strip()
    m = SCI.match(s)
    if m:
        return float(m.group(1)) * 10 ** int(m.group(2))
    m = NUM.match(s)
    return float(m.group(0)) if m else None


stats = collections.Counter()
for r in T:
    at, ans, q = r["answer_type"], r["answer"].strip(), r["question"]
    if at in ("Integer", "Float"):
        v = parse_num(ans)
        stats[f"{at}: parses"] += 1 if v is not None else 0
        stats[f"{at}: FAILS"] += 1 if v is None else 0
        if v is not None and not NUM.fullmatch(ans.replace(",", "")):
            stats[f"{at}: has units/extra"] += 1
    elif at == "Multiple Choice":
        letters = set(OPT.findall(q))
        is_letter = bool(re.fullmatch(r"[A-E]", ans))
        if is_letter and len(letters) >= 2:
            stats["MCQ: lettered options + letter gold"] += 1
        elif is_letter:
            stats["MCQ: letter gold but NO options in question"] += 1
        else:
            stats["MCQ: gold is not a letter"] += 1

for k in sorted(stats):
    print(f"  {k:48s} {stats[k]}")

print("\n--- examples of unparseable / odd golds ---")
n = 0
for r in T:
    at, ans = r["answer_type"], r["answer"].strip()
    if at in ("Integer", "Float") and parse_num(ans) is None:
        print(f"  [{at}] {ans!r}")
        n += 1
        if n >= 12:
            break
