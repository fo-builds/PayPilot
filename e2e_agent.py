import json
from agent import run_agent
r = run_agent("mechanical keyboard", budget=100)
print(json.dumps(r, indent=2))
assert r["ok"], "agent loop failed"
print("E2E PASS: agent searched, picked, and captured COMPLETED:", r["order_id"], r["capture"]["capture_id"])
