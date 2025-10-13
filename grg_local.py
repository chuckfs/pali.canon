#!/usr/bin/env python
# grg_local.py
import sys, json
from planner import plan_query
from retriever import retrieve
from synthesizer import synthesize

def main():
    if len(sys.argv) < 2:
        print("Usage: python grg_local.py \"your question\"")
        return
    q = sys.argv[1]
    plan = plan_query(q)
    hits = retrieve(plan, top_k=8)
    ans = synthesize(q, plan, hits)
    print("\n=== ANSWER ===\n")
    print(ans)
    print("\n=== DEBUG ===")
    print(json.dumps({"plan": plan, "hits": len(hits)}, indent=2))

if __name__ == "__main__":
    main()
