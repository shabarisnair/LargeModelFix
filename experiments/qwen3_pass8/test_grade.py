"""Offline checks for the AIME/DAG grader. Run: python test_grade.py"""
import json
import sys

from grade import extract_json, answer_of, dag_health

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


GOOD = {"steps": [
    {"step_id": 1, "edge": "From the problem statement.", "direct_dependent_steps": None,
     "node": "Let $n$ be the number."},
    {"step_id": 2, "edge": "Using Step 1, apply algebra.", "direct_dependent_steps": [1],
     "node": "We get $n = 70$."},
    {"step_id": 3, "edge": "From Step 2 we conclude.", "direct_dependent_steps": [2],
     "node": "The final answer is $\\boxed{70}$."}]}

# --- extraction ---
check("bare json", extract_json(json.dumps(GOOD))[0]["step_id"], 1)
check("fenced json", extract_json("```json\n" + json.dumps(GOOD) + "\n```")[2]["step_id"], 3)
check("json with trailing prose",
      len(extract_json(json.dumps(GOOD) + "\n\nHope that helps!")), 3)
check("json with leading prose",
      len(extract_json("Here is the solution:\n" + json.dumps(GOOD))), 3)
check("braces inside strings survive",
      extract_json('{"steps":[{"step_id":1,"edge":"set $\\\\{1,2\\\\}$","direct_dependent_steps":null,'
                   '"node":"The final answer is $\\\\boxed{5}$."}]}')[0]["step_id"], 1)
check("not json", extract_json("no json here at all"), None)
check("empty steps rejected", extract_json('{"steps": []}'), None)

# --- answer extraction ---
check("boxed answer", answer_of(GOOD["steps"]), "70")
check("unboxed final answer",
      answer_of([{"step_id": 1, "node": "The final answer is 123."}]), "123")
check("no answer", answer_of([{"step_id": 1, "node": "Let $x=2$."}]), None)

# --- DAG health ---
h = dag_health(GOOD["steps"])
check("good dag well_formed", h["well_formed"], True)
check("good dag roots", h["roots"], 1)

bad_topo = [dict(GOOD["steps"][0]),
            {"step_id": 2, "edge": "From Step 3.", "direct_dependent_steps": [3],
             "node": "x"},
            {"step_id": 3, "edge": "From Step 2.", "direct_dependent_steps": [2],
             "node": "The final answer is $\\boxed{1}$."}]
check("forward dependency caught", dag_health(bad_topo)["topological"], False)

# bad example 1 from bad_examples.txt: deps present but not cited as "Step N" in edge
uncited = [dict(GOOD["steps"][0]),
           {"step_id": 2, "edge": "Using the confirmed values, we sum them.",
            "direct_dependent_steps": [1], "node": "The final answer is $\\boxed{9}$."}]
check("uncited dependency caught", dag_health(uncited)["citations_ok"], False)

# bad example 2: plural grouping "Steps 8, 9, and 10"
plural = [dict(GOOD["steps"][0]),
          {"step_id": 2, "edge": "From Steps 1, we go on.", "direct_dependent_steps": [1],
           "node": "The final answer is $\\boxed{9}$."}]
check("plural citation caught", dag_health(plural)["plural_citation"], True)
check("plural makes it not well formed", dag_health(plural)["well_formed"], False)

# closure: step 1 is never used by a later step
noclose = [{"step_id": 1, "edge": "fact", "direct_dependent_steps": None, "node": "a"},
           {"step_id": 2, "edge": "fact", "direct_dependent_steps": None,
            "node": "The final answer is $\\boxed{3}$."}]
check("closure violation caught", dag_health(noclose)["closure"], False)

# --- LaTeX backslashes make the model's JSON invalid; the parser must repair it ---
from grade import repair_json_escapes  # noqa: E402

latex = ('{"steps":[{"step_id":1,"edge":"Let $S = \\{1,\\ldots,10\\}$ by Step 0.",'
         '"direct_dependent_steps":null,"node":"The final answer is $\\boxed{42}$."}]}')
steps = extract_json(latex)
check("latex json recovered", steps is not None, True)
if steps:
    check("latex answer", answer_of(steps), "42")
    check("latex text preserved", "\\ldots" in steps[0]["edge"], True)
check("valid escapes untouched", repair_json_escapes(r'{"a":"line\nbreak é"}'),
      r'{"a":"line\nbreak é"}')
check("bad \\u repaired", json.loads(repair_json_escapes(r'{"a":"\usr\local"}'))["a"],
      r"\usr\local")
check("outside strings untouched", repair_json_escapes('{"a": 1}'), '{"a": 1}')
if fails:
    print(f"FAILED {len(fails)}:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all AIME/DAG grader checks passed (including LaTeX repair)")

# --- \b \f \r \t are legal JSON escapes, so single-backslash LaTeX gets destroyed ---
for cmd, txt in [("boxed", r'{"a":"$\boxed{204}$"}'), ("frac", r'{"a":"$\frac{1}{2}$"}'),
                 ("right", r'{"a":"$\right)$"}'), ("times", r'{"a":"$3 \times 4$"}')]:
    got = json.loads(repair_json_escapes(txt))["a"]
    check(f"latex \\{cmd} survives", "\\" + cmd in got, True)
    check(f"no control char from \\{cmd}", any(ch in got for ch in "\b\f\r\t"), False)
# a real newline escape must still work
check("real \\n still a newline", json.loads(repair_json_escapes(r'{"a":"x\ny"}'))["a"], "x\ny")
# \boxed mangling used to break answer extraction outright
mangled = r'{"steps":[{"step_id":1,"edge":"e","direct_dependent_steps":null,' \
          r'"node":"The final answer is $\boxed{204}$."}]}'
check("answer recovered from single-backslash boxed", answer_of(extract_json(mangled)), "204")

# --- steps-only format: steps are plain strings ---
so = ('{"steps":["Let $n$ be the number.","We get $n = 70$.",'
      '"The final answer is $\\boxed{70}$."]}')
steps = extract_json(so)
check("stepsonly parsed", steps is not None and len(steps), 3)
check("stepsonly answer", answer_of(steps), "70")
h = dag_health(steps)
check("stepsonly n_steps", h["n_steps"], 3)
check("stepsonly dag checks are N/A", h["contiguous_ids"], None)
check("stepsonly single-backslash boxed",
      answer_of(extract_json(r'{"steps":["The final answer is $\boxed{204}$."]}')), "204")
