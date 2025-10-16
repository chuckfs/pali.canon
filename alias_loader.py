#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load canonical aliases from CSV/YAML and provide fuzzy matching.
Env:
  LOTUS_ALIAS_CSV  -> path to CSV with columns: canonical_id,alias
  LOTUS_ALIAS_YAML -> path to YAML mapping: {canonical_id: [alias1, alias2, ...]}
Dependencies (optional but recommended):
  pip install rapidfuzz pyyaml
"""
from __future__ import annotations
import os, csv, unicodedata
from typing import Dict, List, Tuple, Optional

try:
    import yaml  # optional
except Exception:
    yaml = None

try:
    from rapidfuzz import process, fuzz  # optional
except Exception:
    process, fuzz = None, None


def _strip_diacritics(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def load_aliases() -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """
    Returns:
      id_to_aliases: { "SN 35.28": ["Fire Sermon", "Ādittapariyāya", ...], ... }
      alias_to_id:   { "fire sermon": "SN 35.28", "adittapariyaya": "SN 35.28", ... }
    Stores both raw and diacritic-stripped forms for each alias.
    """
    csv_path = os.getenv("LOTUS_ALIAS_CSV", "")
    yaml_path = os.getenv("LOTUS_ALIAS_YAML", "")
    id_to_aliases: Dict[str, List[str]] = {}
    alias_to_id: Dict[str, str] = {}

    # CSV
    if csv_path and os.path.exists(csv_path):
        with open(csv_path, newline='', encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                cid = (row.get("canonical_id") or "").strip()
                alias = (row.get("alias") or "").strip()
                if cid and alias:
                    id_to_aliases.setdefault(cid, []).append(alias)

    # YAML
    if yaml_path and os.path.exists(yaml_path) and yaml:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            for cid, aliases in data.items():
                for alias in (aliases or []):
                    id_to_aliases.setdefault(cid, []).append(str(alias))

    # Build alias_to_id with both raw and plain forms
    for cid, aliases in id_to_aliases.items():
        for a in aliases + [cid]:
            k1 = a.lower().strip()
            k2 = _strip_diacritics(k1)
            alias_to_id[k1] = cid
            alias_to_id[k2] = cid

    return id_to_aliases, alias_to_id


def fuzzy_ids(text: str, alias_to_id: Dict[str, str], top_n: int = 3, threshold: int = 85) -> List[str]:
    """
    Return candidate canonical IDs via fuzzy match. Falls back to exact contains if rapidfuzz not installed.
    """
    q_raw = (text or "").lower()
    q_plain = _strip_diacritics(q_raw)

    # exact contains first
    found = []
    for key, cid in alias_to_id.items():
        if key in q_raw or key in q_plain:
            if cid not in found:
                found.append(cid)
                if len(found) >= top_n:
                    return found

    if not process:
        return found

    keys = list(alias_to_id.keys())
    matches = process.extract(q_plain, keys, scorer=fuzz.WRatio, limit=10)
    for key, score, _ in matches:
        if score >= threshold:
            cid = alias_to_id.get(key)
            if cid and cid not in found:
                found.append(cid)
                if len(found) >= top_n:
                    break
    return found
