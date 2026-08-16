"""Check the official LiveCodeBench executor actually runs and discriminates.

Uses hand-made samples (one stdin-style, one functional/leetcode-style) with a known
correct and a known wrong solution, so a True and a False are both exercised.
"""
import json
import sys

sys.path.insert(0, "/hdd1/ssn899/LargeModelFix/datasets/livecodebench/LiveCodeBench")
from lcb_runner.evaluation import codegen_metrics, extract_instance_results  # noqa: E402
from lcb_runner.utils.extraction_utils import extract_code  # noqa: E402
from lcb_runner.lm_styles import LMStyle  # noqa: E402

stdin_sample = {"input_output": json.dumps(
    {"inputs": ["3\n", "10\n"], "outputs": ["4\n", "11\n"], "fn_name": None})}
# Functional inputs carry NO trailing newline: the executor does
# [json.loads(line) for line in inputs.split("\n")], so a trailing \n would yield an
# empty line and raise. This matches the real dataset (e.g. input '[5, 2, 3, 1]').
fn_sample = {"input_output": json.dumps(
    {"inputs": ["[1, 2]", "[5, 7]"], "outputs": ["3", "12"], "fn_name": "add"})}

good_stdin = "print(int(input()) + 1)"
bad_stdin = "print(int(input()) + 99)"
good_fn = "class Solution:\n    def add(self, xs):\n        return sum(xs)"
bad_fn = "class Solution:\n    def add(self, xs):\n        return 0"

samples = [stdin_sample, fn_sample]
generations = [[good_stdin, bad_stdin], [good_fn, bad_fn]]

_, results, _ = codegen_metrics(samples, generations, k_list=[1],
                                num_process_evaluate=4, timeout=6)
graded = extract_instance_results(results)
print("\nstdin  [good, bad] ->", graded[0])
print("functional [good, bad] ->", graded[1])

# the extractor must pull the LAST fenced block out of a full model answer
answer = ("Here is my reasoning.\n\n```python\n# a draft\nprint(0)\n```\n\n"
          "Actually, the final version:\n\n```python\nprint(int(input()) + 1)\n```\n")
code = extract_code(answer, LMStyle.OpenAIChat)
print("extract_code ->", repr(code))

ok = (graded[0] == [True, False] and graded[1] == [True, False]
      and code == "print(int(input()) + 1)")
print("\nPASS" if ok else "\nFAIL")
sys.exit(0 if ok else 1)
