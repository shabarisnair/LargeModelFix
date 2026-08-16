"""Offline checks for the graders. Run: python test_grade.py"""
import math
import sys

from grade import extract_boxed, parse_number, grade_numeric, grade_mcq

fails = []


def check(name, got, want):
    if isinstance(got, float) and isinstance(want, float):
        ok = math.isclose(got, want, rel_tol=1e-9)
    else:
        ok = got == want
    if not ok:
        fails.append(f"{name}: got {got!r}, want {want!r}")


# --- boxed extraction ---
check("boxed simple", extract_boxed(r"so \boxed{42}"), "42")
check("boxed nested", extract_boxed(r"\boxed{\frac{1}{2}}"), r"\frac{1}{2}")
check("boxed last wins", extract_boxed(r"\boxed{1} then \boxed{7}"), "7")
check("boxed none", extract_boxed("no answer here"), None)

# --- number parsing ---
for s, want in [("42", 42.0), ("3.14", 3.14), ("-0.5", -0.5), ("1,234", 1234.0),
                (r"65 \text{ m}", 65.0), (r"2.1 \times 10^{-5}", 2.1e-5),
                ("1.8e-5", 1.8e-5), ("21 x 10^-6", 2.1e-5), (r"\frac{1}{2}", 0.5),
                (r"18.51\,\mathrm{N}", 18.51), ("$1860", 1860.0)]:
    check(f"parse {s!r}", parse_number(s), want)
check("parse garbage", parse_number("reinforcers"), None)

# --- numeric grading ---
INT = {"gold_value": 18.0, "is_integer": True}
FLT = {"gold_value": 65.0, "is_integer": False}
check("int exact", grade_numeric({"final_answer": r"\boxed{18}"}, INT)[0], True)
check("int wrong", grade_numeric({"final_answer": r"\boxed{19}"}, INT)[0], False)
check("int as float", grade_numeric({"final_answer": r"\boxed{18.0}"}, INT)[0], True)
check("float within tol", grade_numeric({"final_answer": r"\boxed{64.8}"}, FLT)[0], True)
check("float outside tol", grade_numeric({"final_answer": r"\boxed{61.0}"}, FLT)[0], False)
check("float w/ units", grade_numeric({"final_answer": r"\boxed{65 \text{ m}}"}, FLT)[0], True)
check("no boxed -> wrong", grade_numeric({"final_answer": "the answer is 18"}, INT)[0], False)
check("empty (truncated) -> wrong", grade_numeric({"final_answer": ""}, INT)[0], False)

# --- mcq grading ---
check("mcq ok", grade_mcq({"final_answer": r"\boxed{C}", "gold": "C"}, {})[0], True)
check("mcq lower", grade_mcq({"final_answer": r"\boxed{c}", "gold": "C"}, {})[0], True)
check("mcq wrong", grade_mcq({"final_answer": r"\boxed{A}", "gold": "C"}, {})[0], False)
check("mcq none", grade_mcq({"final_answer": "I think C", "gold": "C"}, {})[0], False)

if fails:
    print(f"FAILED {len(fails)}:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all grader checks passed")
