"""Checks for the trace-reuse rule. Run: python test_reuse.py"""
import sys

from generate import is_reusable, LEGACY_CONFIG

CFG = {"model": "M", "max_tokens": 45000, "temperature": 0.6, "top_p": 0.95,
       "top_k": 20, "prompt_version": "v2"}


def row(**kw):
    """A legacy-shaped row, but tagged v2 so prompt version is not the thing under test."""
    r = {"model": "M", "finish_reason": "stop", "completion_tokens": 1000,
         "config": dict(LEGACY_CONFIG, prompt_version="v2")}
    r.update(kw)
    return r


fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got}, want {want}")


# same config -> reuse
check("identical config",
      is_reusable(row(config={"max_tokens": 45000, "temperature": 0.6, "top_p": 0.95,
                              "top_k": 20, "prompt_version": "v2"}), CFG), True)

# --- prompt versioning: a trace from different prompt text is a different experiment ---
check("v1 prompt under v2 run",
      is_reusable(row(config=dict(LEGACY_CONFIG, prompt_version="v1")), CFG), False)
check("v1 prompt, same max_tokens, still refused",
      is_reusable(row(config=dict(LEGACY_CONFIG, prompt_version="v1",
                                  max_tokens=45000)), CFG), False)
check("row with no config at all is treated as v1 -> refused",
      is_reusable({"model": "M", "finish_reason": "stop",
                   "completion_tokens": 500}, CFG), False)
# old 38k cap that never bound -> reusable under 45k
check("38k stopped naturally", is_reusable(row(), CFG), True)
# old 38k cap that DID bind -> must regenerate
check("38k truncated", is_reusable(row(finish_reason="length",
                                       completion_tokens=38000), CFG), False)
# different model -> never reuse
check("other model", is_reusable(row(model="OTHER"), CFG), False)
# v2-era config, so these cases isolate sampling/max_tokens from prompt version
def v2(**kw):
    return dict(LEGACY_CONFIG, prompt_version="v2", **kw)


# different sampling -> never reuse
check("other temperature", is_reusable(row(config=v2(temperature=1.0)), CFG), False)
check("other top_p", is_reusable(row(config=v2(top_p=0.9)), CFG), False)
# a longer old cap is fine if the trace fits inside the new one
check("60k cap, short trace",
      is_reusable(row(config=v2(max_tokens=60000), completion_tokens=1000), CFG), True)
# a longer old cap whose trace exceeds the new cap -> not reusable
check("60k cap, 50k trace",
      is_reusable(row(config=v2(max_tokens=60000), completion_tokens=50000), CFG), False)
# a v1-era row IS reusable by a v1 run (the prompt matches), 38k cap notwithstanding
V1CFG = dict(CFG, prompt_version="v1")
check("legacy row under a v1 run",
      is_reusable({"model": "M", "finish_reason": "stop",
                   "completion_tokens": 500}, V1CFG), True)

if fails:
    print("FAILED:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all reuse checks passed")
