#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI runner: Mistral (planner) -> Chroma (RAG) -> Mistral (synth).
Adds optional flags to override basket/nikāya constraints and top_k.
"""

from __future__ import annotations
import os
import argparse
import json

from planner import plan_query
from retriever import retrieve
from synthesizer import synthesize


def main():
    ap = argparse.ArgumentParser(description="Query the Pāli Canon with grounded citations.")
    ap.add_argument("question", nargs="+", help="Your question about the Canon.")
    ap.add_argument("--basket", choices=["sutta", "vinaya", "abhidhamma"],
                    help="Force a basket filter (overrides planner).")
    ap.add_argument("--nikaya", choices=["DN", "MN", "SN", "AN", "KN"],
                    help="Force a Nikāya filter (overrides planner).")
    ap.add_argument("-k", "--top_k", type=int, default=int(os.getenv("TOP_K", "8")),
                    help="How many chunks to retrieve (default: 8).")
    ap.add_argument("--no-citations", action="store_true",
                    help="Do not append Sources section (not recommended).")
    args = ap.parse_args()

    q = " ".join(args.question)

    if os.getenv("DEBUG_RAG", "0") == "1":
        print("USING ENV:", {
            "PALI_PROJECT_ROOT": os.getenv("PALI_PROJECT_ROOT"),
            "LOTUS_CHROMA_DIR": os.getenv("LOTUS_CHROMA_DIR"),
            "LOTUS_CHROMA_COLLECTION": os.getenv("LOTUS_CHROMA_COLLECTION"),
            "LOTUS_EMBED_MODEL": os.getenv("LOTUS_EMBED_MODEL"),
            "LOTUS_LLM_MODEL": os.getenv("LOTUS_LLM_MODEL", "mistral"),
        })

    plan = plan_query(q)
    c = plan.setdefault("constraints", {})
    if args.basket:
        c["basket"] = args.basket
    if args.nikaya:
        c["nikaya"] = args.nikaya
    if args.no_citations:
        plan["require_citations"] = False

    hits = retrieve(plan, top_k=args.top_k)
    ans = synthesize(q, plan, hits)

    print("\n=== ANSWER ===\n")
    print(ans)

    if os.getenv("DEBUG_RAG", "0") == "1":
        top_cites = [h["meta"].get("citation", "") for h in hits[:5]]
        dbg = {"plan": plan, "hits": len(hits), "top_citations": top_cites}
        print("\n=== DEBUG ===")
        print(json.dumps(dbg, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()