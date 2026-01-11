# Evaluation Guide

This document describes how to evaluate the quality of pali.canon's retrieval and answer generation.

## Why Evaluation Matters

Without measurement, you cannot improve. Every change to the RAG pipeline—chunk size, embedding model, prompt wording—could help or hurt quality. Evaluation tells you which.

**The core questions:**
1. **Retrieval:** Does the system find the right passages?
2. **Faithfulness:** Does the answer reflect the retrieved passages (not hallucinate)?
3. **Relevance:** Does the answer actually address the question?

---

## Golden Dataset

A "golden set" is a collection of question-answer pairs with known correct answers. This is the foundation of all evaluation.

### Schema

```json
{
  "id": 1,
  "question": "What is the Fire Sermon about?",
  "expected_refs": ["SN 35.28"],
  "expected_pdfs": ["samyutta_nikaya4.pdf"],
  "expected_keywords": ["burning", "sense bases", "passion", "aversion", "delusion", "fire"],
  "ground_truth_summary": "The Buddha teaches that all sense bases are burning with the fires of passion, aversion, and delusion.",
  "difficulty": "easy",
  "category": "sutta_lookup"
}
```

### Sample Golden Set (eval/golden_set.json)

```json
[
  {
    "id": 1,
    "question": "What is the Fire Sermon about?",
    "expected_refs": ["SN 35.28"],
    "expected_pdfs": ["samyutta_nikaya4.pdf"],
    "expected_keywords": ["burning", "fire", "passion", "aversion", "sense"],
    "ground_truth_summary": "The Buddha declares that all sense bases are burning with the fires of passion, aversion, and delusion.",
    "difficulty": "easy",
    "category": "sutta_lookup"
  },
  {
    "id": 2,
    "question": "What simile does the Buddha use to teach patience?",
    "expected_refs": ["MN 21"],
    "expected_pdfs": ["majjhima_nikaya1.pdf"],
    "expected_keywords": ["saw", "patience", "loving-kindness", "bandits"],
    "ground_truth_summary": "In the Simile of the Saw (MN 21), even if bandits sawed off one's limbs, giving rise to hate would not follow the teaching.",
    "difficulty": "easy",
    "category": "sutta_lookup"
  },
  {
    "id": 3,
    "question": "What are the five aggregates?",
    "expected_refs": ["SN 22.59"],
    "expected_pdfs": ["samyutta_nikaya3.pdf"],
    "expected_keywords": ["form", "feeling", "perception", "formations", "consciousness"],
    "ground_truth_summary": "Form, feeling, perception, volitional formations, and consciousness.",
    "difficulty": "easy",
    "category": "concept"
  }
]
```

---

## Metrics

### Retrieval Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Recall@k** | found / expected | Fraction of expected docs in top k |
| **Hit Rate** | 1 if any match, else 0 | At least one relevant doc found |
| **MRR** | 1 / rank of first match | How high is first relevant result |
| **Keyword Coverage** | found_kw / expected_kw | Terms present in retrieved text |

### Answer Metrics

| Metric | Method | Scale |
|--------|--------|-------|
| **Faithfulness** | LLM-as-judge | 1-5 |
| **Relevance** | LLM-as-judge | 1-5 |
| **Quote Accuracy** | String match | % valid |

---

## Running Evaluations

### Basic Retrieval Evaluation

```python
# scripts/eval_retrieval.py
from planner import plan
from retriever import retrieve
import json

def evaluate(golden_set_path, k=10):
    with open(golden_set_path) as f:
        golden = json.load(f)
    
    results = []
    for item in golden:
        p = plan(item["question"])
        hits = retrieve(p, k=k)
        
        retrieved_pdfs = {h["pdf_name"] for h in hits}
        expected_pdfs = set(item.get("expected_pdfs", []))
        
        recall = len(retrieved_pdfs & expected_pdfs) / len(expected_pdfs) if expected_pdfs else 0
        
        results.append({"id": item["id"], "recall": recall})
    
    avg_recall = sum(r["recall"] for r in results) / len(results)
    print(f"Average Recall@{k}: {avg_recall:.2%}")
    return results
```

Run:
```bash
python scripts/eval_retrieval.py eval/golden_set.json
```

### Faithfulness Evaluation

```python
JUDGE_PROMPT = """Score how well the answer reflects the sources (1-5):
5 = All claims supported
3 = Mixed supported/unsupported
1 = Contradicts sources

Question: {question}
Sources: {context}
Answer: {answer}

SCORE:"""
```

---

## Interpreting Results

| Metric | Poor | OK | Good |
|--------|------|-----|------|
| Recall@10 | <50% | 50-80% | >80% |
| MRR | <0.3 | 0.3-0.6 | >0.6 |
| Faithfulness | <3 | 3-4 | >4 |

### Common Issues

**Low Recall:** Embeddings miss relevant docs → try hybrid search, query expansion
**Low MRR:** Relevant docs ranked low → add reranking
**Low Faithfulness:** LLM ignores context → strengthen grounding prompt

---

## Continuous Tracking

Save results with timestamps:
```
eval/results/
├── 2024-01-15_baseline.json
├── 2024-01-20_larger_chunks.json
└── summary.csv
```

Track in CSV:
```csv
date,experiment,recall,mrr,notes
2024-01-15,baseline,0.65,0.42,Initial
2024-01-20,chunk_1500,0.71,0.45,Improved
```

---

## Minimum Viable Eval

If you do nothing else:

1. Create 10 golden Q&A pairs from suttas you know
2. Run retrieval, check if expected PDFs appear
3. Read 10 generated answers, note hallucinations
4. Track these numbers over time

This takes 2 hours and gives you baseline quality visibility.
