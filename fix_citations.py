#!/usr/bin/env python3
"""Quick fix for citation extraction issues."""

# Test the fix
from indexer import _extract_citations

test_cases = [
    ("See SN 35.28", ["SN 35.28"]),
    ("see sn 35.28", ["SN 35.28"]),
    ("Compare MN 21 and DN 22, also see SN 35.28", ["MN 21", "DN 22", "SN 35.28"]),
    ("Ādittapariyāya Sutta", ["SN 35.28"]),
    ("Satipaṭṭhāna Sutta and Ādittapariyāya", ["MN 10", "SN 35.28"]),
]

print("Testing citation extraction fixes:")
for text, expected in test_cases:
    result = _extract_citations(text)
    status = "✓" if all(e in result for e in expected) else "✗"
    print(f"{status} {text[:40]:40} -> {result}")
