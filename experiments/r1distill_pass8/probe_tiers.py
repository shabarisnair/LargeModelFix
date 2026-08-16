"""How many WebInstruct rows are *semantically* deterministic, not merely parseable?

Tiers, strictest first:
  A  MCQ: lettered options in the question AND a single-letter gold
  B  bare integer gold ("18")
  C  bare decimal gold ("3.14", "1.8e-5") -- deterministic up to a rounding tolerance
  D  number + trailing unit ("65 m") -- gradeable only if the unit is pinned down
  E  number buried in prose / multi-part -- needs a judge
"""
import re
import collections
import pyarrow.parquet as pq

T = pq.read_table("/hdd1/ssn899/LargeModelFix/datasets/webinstruct/"
                  "data/test-00000-of-00001.parquet").to_pylist()

NUM = r"[+-]?(?:\d+\.?\d*|\.\d+)"
SCI = rf"{NUM}\s*(?:[x×*]\s*10\s*\^?\s*[+-]?\{{?\d+\}}?|[eE][+-]?\d+)"
NUM_RE = re.compile(f"(?:{SCI})|(?:{NUM})")
BARE_INT = re.compile(r"^[+-]?\d+$")
BARE_DEC = re.compile(f"^(?:{SCI})$|^{NUM}$")
OPT_RE = re.compile(r"(?:^|[\s|(])([A-E])[\)\.]\s", re.M)
# a trailing unit: short, letter/symbol-only token(s) after the number
UNIT_TAIL = re.compile(
    r"^\s*[a-zA-ZΩµμ°%/^\d\.\*\-\s\$]{1,18}$")

tiers = collections.Counter()
examples = collections.defaultdict(list)

for r in T:
    at, gold, q = r["answer_type"], r["answer"].strip(), r["question"]
    g = gold.replace(",", "").replace("$", "").strip()
    if at == "Multiple Choice":
        if re.fullmatch(r"[A-E]", gold) and len(set(OPT_RE.findall(q))) >= 2:
            t = "A"
        else:
            t = "E"
    elif at in ("Integer", "Float"):
        nums = NUM_RE.findall(g)
        if len(nums) != 1:
            t = "E"
        elif BARE_INT.fullmatch(g):
            t = "B"
        elif BARE_DEC.fullmatch(g):
            t = "C"
        else:
            tok = NUM_RE.search(g)
            head, tail = g[:tok.start()], g[tok.end():]
            t = "D" if head.strip() == "" and UNIT_TAIL.match(tail) else "E"
    else:
        continue
    tiers[t] += 1
    if len(examples[t]) < 6:
        examples[t].append(gold)

names = {"A": "MCQ w/ options + letter gold", "B": "bare integer",
         "C": "bare decimal", "D": "number + trailing unit",
         "E": "prose / multi-part / ambiguous"}
print(f"{'tier':5s} {'n':>5s}  description")
for t in "ABCDE":
    print(f"  {t:3s} {tiers[t]:5d}  {names[t]}")
print(f"\n  A+B+C (no unit ambiguity) = {tiers['A']+tiers['B']+tiers['C']}")
print(f"  A+B+C+D                   = {tiers['A']+tiers['B']+tiers['C']+tiers['D']}")

for t in "ABCDE":
    print(f"\n[{t}] {names[t]}:")
    for e in examples[t]:
        print("   ", repr(e))
