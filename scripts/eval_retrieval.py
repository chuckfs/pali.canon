#!/usr/bin/env python3
"""Evaluate retrieval quality against golden set."""

import json
import sys
from pathlib import Path

# Add project root to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from planner import plan
from retriever import retrieve


def evaluate_retrieval(golden_set_path: str, k: int = 10):
    """Run retrieval evaluation against golden set."""
    
    with open(golden_set_path) as f:
        golden_set = json.load(f)
    
    results = []
    total_recall = 0
    total_mrr = 0
    total_keyword_coverage = 0
    
    print("\n" + "="*70)
    print("RETRIEVAL EVALUATION")
    print("="*70)
    
    for item in golden_set:
        question = item["question"]
        expected_pdfs = set(item.get("expected_pdfs", []))
        expected_keywords = [kw.lower() for kw in item.get("expected_keywords", [])]
        
        # Run the pipeline
        p = plan(question)
        hits = retrieve(p, k=k)
        
        # Collect retrieved PDFs
        retrieved_pdfs = {h["pdf_name"] for h in hits}
        
        # Calculate Recall
        if expected_pdfs:
            found_pdfs = expected_pdfs & retrieved_pdfs
            recall = len(found_pdfs) / len(expected_pdfs)
        else:
            recall = 0
            found_pdfs = set()
        
        # Calculate MRR (Mean Reciprocal Rank)
        mrr = 0.0
        for i, h in enumerate(hits):
            if h["pdf_name"] in expected_pdfs:
                mrr = 1.0 / (i + 1)
                break
        
        # Calculate Keyword Coverage
        retrieved_text = " ".join(h["text"].lower() for h in hits)
        found_keywords = [kw for kw in expected_keywords if kw in retrieved_text]
        keyword_coverage = len(found_keywords) / len(expected_keywords) if expected_keywords else 0
        
        # Accumulate totals
        total_recall += recall
        total_mrr += mrr
        total_keyword_coverage += keyword_coverage
        
        # Store result
        result = {
            "id": item["id"],
            "question": question,
            "recall": recall,
            "mrr": mrr,
            "keyword_coverage": keyword_coverage,
            "expected_pdfs": list(expected_pdfs),
            "found_pdfs": list(found_pdfs),
            "missing_pdfs": list(expected_pdfs - retrieved_pdfs),
            "found_keywords": found_keywords,
            "missing_keywords": [kw for kw in expected_keywords if kw not in found_keywords],
        }
        results.append(result)
        
        # Print per-question results
        status = "✓" if recall == 1.0 else "✗"
        print(f"\n{status} Q{item['id']}: {question[:50]}...")
        print(f"  Recall: {recall:.0%} | MRR: {mrr:.2f} | Keywords: {keyword_coverage:.0%}")
        if result["missing_pdfs"]:
            print(f"  Missing PDFs: {result['missing_pdfs']}")
        if result["missing_keywords"]:
            print(f"  Missing keywords: {result['missing_keywords'][:5]}...")  # Show first 5
    
    # Calculate averages
    n = len(golden_set)
    avg_recall = total_recall / n if n else 0
    avg_mrr = total_mrr / n if n else 0
    avg_keyword_coverage = total_keyword_coverage / n if n else 0
    perfect_recall_count = sum(1 for r in results if r["recall"] == 1.0)
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Questions evaluated: {n}")
    print(f"Average Recall@{k}:  {avg_recall:.1%}")
    print(f"Average MRR:         {avg_mrr:.2f}")
    print(f"Keyword Coverage:    {avg_keyword_coverage:.1%}")
    print(f"Perfect Recall:      {perfect_recall_count}/{n} ({perfect_recall_count/n:.0%})")
    print("="*70)
    
    # Interpretation
    print("\nINTERPRETATION:")
    if avg_recall >= 0.8:
        print("  Recall: GOOD - Finding most expected documents")
    elif avg_recall >= 0.5:
        print("  Recall: OK - Finding some expected documents, room for improvement")
    else:
        print("  Recall: POOR - Missing many expected documents")
    
    if avg_mrr >= 0.6:
        print("  MRR: GOOD - Relevant docs ranking high")
    elif avg_mrr >= 0.3:
        print("  MRR: OK - Relevant docs present but not top-ranked")
    else:
        print("  MRR: POOR - Relevant docs ranking low or missing")
    
    if avg_keyword_coverage >= 0.7:
        print("  Keywords: GOOD - Retrieved text contains expected terms")
    elif avg_keyword_coverage >= 0.5:
        print("  Keywords: OK - Some expected terms found")
    else:
        print("  Keywords: POOR - Missing many expected terms")
    
    return {
        "summary": {
            "total_questions": n,
            "avg_recall": avg_recall,
            "avg_mrr": avg_mrr,
            "avg_keyword_coverage": avg_keyword_coverage,
            "perfect_recall_count": perfect_recall_count,
        },
        "per_question": results
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality")
    parser.add_argument("golden_set", nargs="?", default="eval/golden_set.json",
                        help="Path to golden_set.json (default: eval/golden_set.json)")
    parser.add_argument("--k", type=int, default=10, help="Top-k for retrieval (default: 10)")
    parser.add_argument("--output", "-o", help="Save full results to JSON file")
    args = parser.parse_args()
    
    results = evaluate_retrieval(args.golden_set, k=args.k)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nFull results saved to: {args.output}")


if __name__ == "__main__":
    main()
