"""Checks for the v3/v4 step-annotation parser, including the collisions measured in the
v1 traces (4,103 steps end with a bare "[N,...]" — almost all LiveCodeBench code)."""
import sys

from parse_annotated import parse_trace, to_dag

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


# --- v3: leading marker ---
v3 = ("{0} first step\n\n"
      "{1} unrelated fresh start\n\n"
      "{2} -> [0,1] combines them\n\n"
      "{3} -> [1] follows only from one")
p = parse_trace(v3, "v3")
check("v3 defects", p.defects, [])
check("v3 n", len(p.steps), 4)
check("v3 deps", [s.deps for s in p.steps], [[], [], [0, 1], [1]])
check("v3 text0", p.steps[0].text, "first step")
check("v3 text2", p.steps[2].text, "combines them")
check("v3 roots", to_dag(p)["roots"], [0, 1])

# --- v4: trailing marker ---
v4 = ("{0} first step\n\n"
      "{1} unrelated fresh start\n\n"
      "{2} combines them [0,1]\n\n"
      "{3} follows only from one [1]")
p = parse_trace(v4, "v4")
check("v4 defects", p.defects, [])
check("v4 deps", [s.deps for s in p.steps], [[], [], [0, 1], [1]])
check("v4 text2", p.steps[2].text, "combines them")

# --- the collision the measurement found: code ending in a bare bracket list ---
code = ("{0} set up the dp table\n\n"
        "{1} the base case is return [0,1]\n\n"
        "{2} print(dp[0])\n\n"
        "{3} final answer uses both [1,2]")
p = parse_trace(code, "v4")
check("v4 code-like steps keep their text",
      [s.text for s in p.steps][1:3], ["the base case is return [0,1]", "print(dp[0])"])
check("v4 code-like steps claim no deps", [s.deps for s in p.steps], [[], [], [], [1, 2]])
check("v4 flags the ambiguous trailing list", any("not a valid dependency set" in d
                                                  for d in p.defects), True)

# v3 must be equally immune (list is at the front, code at the back)
p = parse_trace("{0} a\n\n{1} return [0,1]\n\n{2} -> [0] b", "v3")
check("v3 code-like", [s.deps for s in p.steps], [[], [], [0]])

# --- LaTeX-ish text must not be read as a marker ---
p = parse_trace("{0} we get \\frac{1}{2}\n\n{1} -> [0] so x = [1,2] is the interval", "v3")
check("v3 latex/interval deps", [s.deps for s in p.steps], [[], [0]])
check("v3 latex text kept", p.steps[1].text, "so x = [1,2] is the interval")

# --- defect reporting ---
p = parse_trace("{0} a\n\n{2} -> [0] skipped one", "v3")
check("skipped index flagged", bool(p.defects), True)
p = parse_trace("{0} a\n\n{1} -> [3] forward ref", "v3")
check("forward reference flagged", any("not strictly earlier" in d for d in p.defects), True)
p = parse_trace("plain paragraph with no marker\n\n{1} b", "v3")
check("missing marker flagged", any("no {index}" in d for d in p.defects), True)

# --- whitespace tolerance inside the list ---
p = parse_trace("{0} a\n\n{1} b\n\n{2} -> [0, 1] c", "v3")
check("spaces inside list tolerated", p.steps[2].deps, [0, 1])

if fails:
    print(f"FAILED {len(fails)}:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all v3/v4 parser checks passed")
